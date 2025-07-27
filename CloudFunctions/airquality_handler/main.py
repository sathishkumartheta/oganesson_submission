'''v4'''
import requests
import os
from datetime import datetime, timezone
from google.cloud import firestore
from google.cloud import pubsub_v1
import json
import pytz  # 👈 Required for IST timezone handling

# --- Configuration ---
# Google Cloud Project ID for Firestore
# It's recommended to fetch this from the environment for Cloud Functions
# The 'GCP_PROJECT' environment variable is automatically set by Cloud Functions.
PROJECT_ID = os.getenv('GCP_PROJECT') 
if not PROJECT_ID:
    # Fallback if GCP_PROJECT isn't automatically set (e.g., local testing without gcloud env)
    PROJECT_ID = "cityinsightmaps" # Replace with your actual project ID if not using GCP_PROJECT env var

# OpenWeatherMap API Key - Set this as an environment variable in your Cloud Function
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    print("Error: API_KEY environment variable not set. Please set it in Cloud Function config.")

# Pub/Sub Topic ID for AQI Updates
# IMPORTANT: This should be the actual name of your Pub/Sub topic, e.g., "bengaluru_aqi_updates"
PUBSUB_TOPIC_ID_AQI = os.getenv('PUBSUB_TOPIC_ID_AQI')

if not PUBSUB_TOPIC_ID_AQI:
    print("Warning: PUBSUB_TOPIC_ID_AQI environment variable not set. Air quality data will NOT be published to Pub/Sub.")


# Initialize Firestore client globally to reuse connection
# It's good practice to initialize outside the function if possible for performance,
# but also handle potential initialization errors if the env var isn't ready.
db = None
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    print(f"Firestore client initialization failed at global scope: {e}")

# Initialize Pub/Sub publisher client globally 
pubsub_publisher_client = None
try:
    pubsub_publisher_client = pubsub_v1.PublisherClient()
except Exception as e:
    print(f"Pub/Sub PublisherClient initialization failed at global scope: {e}")


# --- Define Important City Points for Bengaluru ---
# You can add more points as needed to cover your definition of "whole city limits"
# Consider major intersections, tech parks, residential hubs, etc.
BENGALURU_LOCATIONS = {
    "City_Centre_Majestic": {"lat": 12.9762, "lon": 77.5713},  # Majestic, Bus Stand/Railway Station area
    "Koramangala": {"lat": 12.9345, "lon": 77.6190},     # Popular residential/commercial area
    "Electronic_City": {"lat": 12.8465, "lon": 77.6631}, # Major tech hub in south
    "Whitefield": {"lat": 12.9698, "lon": 77.7500},      # Major tech hub in east
    "Yelahanka": {"lat": 13.1007, "lon": 77.5750},       # North Bengaluru, near airport road
    "Jayanagar": {"lat": 12.9234, "lon": 77.5870},       # Established residential area
    "Indiranagar": {"lat": 12.9719, "lon": 77.6412},     # Popular commercial/residential
    "Malleshwaram": {"lat": 13.0039, "lon": 77.5683},    # Old Bengaluru, residential
    "Marathahalli": {"lat": 12.9667, "lon": 77.7167}      # Eastern tech corridor
}

# OpenWeatherMap Air Pollution API URL
OPENWEATHER_AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

def get_aqi_category(aqi_value):
    """Maps AQI value to a descriptive category based on OpenWeatherMap's scale."""
    category_map = {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor"
    }
    return category_map.get(aqi_value, "Unknown")

def airquality_handler(request):
    """
    Google Cloud Function to check air quality for a list of important city points
    in Bengaluru using OpenWeatherMap API. It stores a consolidated historical record,
    overwrites the latest snapshot in Firestore, and publishes the latest snapshot to Pub/Sub.

    Args:
        request (flask.Request): The HTTP request object.
                                 This function is designed to be triggered by HTTP (e.g., Cloud Scheduler).
    Returns:
        tuple: A tuple containing the response message (str) and HTTP status code (int).
    """
    global db, pubsub_publisher_client # Access globally initialized Firestore client

    if not API_KEY:
        print("Function exiting due to missing API_KEY.")
        return "❌ Missing API key in environment variables.", 500

    if db is None:
        try: # Try to initialize Firestore client if it failed globally
            db = firestore.Client(project=PROJECT_ID)
            print("Firestore client initialized successfully within function.")
        except Exception as e:
            print(f"Firestore client initialization failed: {e}")
            return "❌ Firestore client could not be initialized. Check logs.", 500

    # 🇮🇳 Get timestamp in IST
    ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
    timestamp = ist_now.strftime("%Y%m%d_%H%M%S")
    
    # This will be the single JSON record stored in Firestore
    consolidated_aqi_data = {
        "city": "Bengaluru",
        "timestamp": timestamp,
        "source": "OpenWeatherMap",
        "locations": [] # List to hold data for each point
    }
    
    overall_status = 200
    error_messages = []

    print(f"Starting air quality data fetch for Bengaluru at {timestamp}")

    for name, coords in BENGALURU_LOCATIONS.items():
        lat = coords["lat"]
        lon = coords["lon"]
        
        params = {'lat': lat, 'lon': lon, 'appid': API_KEY}

        try:
            response = requests.get(OPENWEATHER_AQI_URL, params=params, timeout=30)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            if "list" not in data or not data["list"]:
                print(f"No air quality data available for {name} ({lat}, {lon}).")
                error_messages.append(f"No data for {name}")
                # Continue to next location, don't fail the whole function
                continue 

            aqi_data = data["list"][0] # Get the current AQI data
            
            location_aqi_record = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "aqi": aqi_data.get("main", {}).get("aqi"),
                "aqi_category": get_aqi_category(aqi_data.get("main", {}).get("aqi")),
                "components": aqi_data.get("components", {}),
                "retrieval_status": "success"
            }
            consolidated_aqi_data["locations"].append(location_aqi_record)
            print(f"Successfully retrieved AQI for {name}.")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching AQI for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as an error if any single call fails
            consolidated_aqi_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })
        except Exception as e:
            error_msg = f"An unexpected error occurred for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500
            consolidated_aqi_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })

    # --- Store historical air quality data ---
    # This creates a new document for each run with a timestamped ID.
    historical_doc_id = f"bengaluru_aqi_{timestamp}"
    try:
        db.collection("bengaluru_air_quality").document(historical_doc_id).set(consolidated_aqi_data)
        print(f"✅ Stored historical air quality data with ID: {historical_doc_id}")
    except Exception as e:
        print(f"❌ Error storing historical data to Firestore: {e}")
        error_messages.append(f"Firestore historical storage failed: {e}")
        overall_status = 500

    # --- Overwriting latest value to current_airquality_data Collection ---
    TARGET_COLLECTION_CURRENT = "current_airquality_data"
    FIXED_DOC_ID_CURRENT = "bengaluru_latest_aqi" 
    
    try:
        db.collection(TARGET_COLLECTION_CURRENT).document(FIXED_DOC_ID_CURRENT).set(consolidated_aqi_data)
        print(f"✅ Stored/Overwrote current air quality data in '{TARGET_COLLECTION_CURRENT}' with ID: {FIXED_DOC_ID_CURRENT}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore in '{TARGET_COLLECTION_CURRENT}': {e}")
        error_messages.append(f"Firestore storage failed for latest data: {e}")
        overall_status = 500

    # --- Publish to Pub/Sub (NEW) ---
    if pubsub_publisher_client and PUBSUB_TOPIC_ID_AQI:
        try:
            topic_path = pubsub_publisher_client.topic_path(PROJECT_ID, PUBSUB_TOPIC_ID_AQI)
            # Convert JSON data to a string, then encode to bytes
            data_str = json.dumps(consolidated_aqi_data)
            data_bytes = data_str.encode("utf-8")

            future = pubsub_publisher_client.publish(topic_path, data_bytes)
            message_id = future.result() # Blocks until the message is published
            print(f"✅ Published latest AQI data to Pub/Sub topic '{PUBSUB_TOPIC_ID_AQI}' with message ID: {message_id}")
        except Exception as e:
            error_msg = f"❌ Error publishing AQI data to Pub/Sub topic '{PUBSUB_TOPIC_ID_AQI}': {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as error if Pub/Sub fails
    else:
        if not PUBSUB_TOPIC_ID_AQI:
            print("Skipping Pub/Sub for AQI: PUBSUB_TOPIC_ID_AQI is not set.")
        if not pubsub_publisher_client:
            print("Skipping Pub/Sub for AQI: Pub/Sub client not initialized.")


    if error_messages:
        return f"❌ Completed with errors: {'; '.join(error_messages)}. Stored partial/full data with ID: {historical_doc_id}", overall_status
    else:
        return f"✅ Successfully fetched, stored consolidated air quality data with ID: {historical_doc_id} and published latest air quality data.", 200
		
		
'''v3
import requests
import os
from datetime import datetime, timezone
from google.cloud import firestore

# --- Configuration ---
# Google Cloud Project ID for Firestore
# It's recommended to fetch this from the environment for Cloud Functions
# The 'GCP_PROJECT' environment variable is automatically set by Cloud Functions.
PROJECT_ID = os.getenv('GCP_PROJECT') 
if not PROJECT_ID:
    # Fallback if GCP_PROJECT isn't automatically set (e.g., local testing without gcloud env)
    PROJECT_ID = "cityinsightmaps" # Replace with your actual project ID if not using GCP_PROJECT env var

# OpenWeatherMap API Key - Set this as an environment variable in your Cloud Function
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    print("Error: API_KEY environment variable not set. Please set it in Cloud Function config.")

# Initialize Firestore client globally to reuse connection
# It's good practice to initialize outside the function if possible for performance,
# but also handle potential initialization errors if the env var isn't ready.
db = None
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    print(f"Firestore client initialization failed at global scope: {e}")

# --- Define Important City Points for Bengaluru ---
# You can add more points as needed to cover your definition of "whole city limits"
# Consider major intersections, tech parks, residential hubs, etc.
BENGALURU_LOCATIONS = {
    "City_Centre_Majestic": {"lat": 12.9762, "lon": 77.5713},  # Majestic, Bus Stand/Railway Station area
    "Koramangala": {"lat": 12.9345, "lon": 77.6190},     # Popular residential/commercial area
    "Electronic_City": {"lat": 12.8465, "lon": 77.6631}, # Major tech hub in south
    "Whitefield": {"lat": 12.9698, "lon": 77.7500},      # Major tech hub in east
    "Yelahanka": {"lat": 13.1007, "lon": 77.5750},       # North Bengaluru, near airport road
    "Jayanagar": {"lat": 12.9234, "lon": 77.5870},       # Established residential area
    "Indiranagar": {"lat": 12.9719, "lon": 77.6412},     # Popular commercial/residential
    "Malleshwaram": {"lat": 13.0039, "lon": 77.5683},    # Old Bengaluru, residential
    "Marathahalli": {"lat": 12.9667, "lon": 77.7167}      # Eastern tech corridor
}

# OpenWeatherMap Air Pollution API URL
OPENWEATHER_AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

def get_aqi_category(aqi_value):
    """Maps AQI value to a descriptive category based on OpenWeatherMap's scale."""
    category_map = {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor"
    }
    return category_map.get(aqi_value, "Unknown")

def airquality_handler(request):
    """
    Google Cloud Function to check air quality for a list of important city points
    in Bengaluru using OpenWeatherMap API and store the consolidated response
    as a single JSON record in Firestore.

    Args:
        request (flask.Request): The HTTP request object.
                                 This function is designed to be triggered by HTTP (e.g., Cloud Scheduler).
    Returns:
        tuple: A tuple containing the response message (str) and HTTP status code (int).
    """
    global db # Access the globally initialized Firestore client

    if not API_KEY:
        print("Function exiting due to missing API_KEY.")
        return "❌ Missing API key in environment variables.", 500

    if db is None:
        try: # Try to initialize Firestore client if it failed globally
            db = firestore.Client(project=PROJECT_ID)
            print("Firestore client initialized successfully within function.")
        except Exception as e:
            print(f"Firestore client initialization failed: {e}")
            return "❌ Firestore client could not be initialized. Check logs.", 500

    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # This will be the single JSON record stored in Firestore
    consolidated_aqi_data = {
        "city": "Bengaluru",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "source": "OpenWeatherMap",
        "locations": [] # List to hold data for each point
    }
    
    overall_status = 200
    error_messages = []

    print(f"Starting air quality data fetch for Bengaluru at {time_str}")

    for name, coords in BENGALURU_LOCATIONS.items():
        lat = coords["lat"]
        lon = coords["lon"]
        
        params = {'lat': lat, 'lon': lon, 'appid': API_KEY}

        try:
            response = requests.get(OPENWEATHER_AQI_URL, params=params, timeout=30)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            if "list" not in data or not data["list"]:
                print(f"No air quality data available for {name} ({lat}, {lon}).")
                error_messages.append(f"No data for {name}")
                # Continue to next location, don't fail the whole function
                continue 

            aqi_data = data["list"][0] # Get the current AQI data
            
            location_aqi_record = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "aqi": aqi_data.get("main", {}).get("aqi"),
                "aqi_category": get_aqi_category(aqi_data.get("main", {}).get("aqi")),
                "components": aqi_data.get("components", {}),
                "retrieval_status": "success"
            }
            consolidated_aqi_data["locations"].append(location_aqi_record)
            print(f"Successfully retrieved AQI for {name}.")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching AQI for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as an error if any single call fails
            consolidated_aqi_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })
        except Exception as e:
            error_msg = f"An unexpected error occurred for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500
            consolidated_aqi_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })

    # Generate a unique document ID based on city and timestamp
    doc_id = f"bengaluru_aqi_{time_str}"
    
    try:
        db.collection("bengaluru_air_quality").document(doc_id).set(consolidated_aqi_data)
        print(f"✅ Stored consolidated air quality data with ID: {doc_id}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore: {e}")
        error_messages.append(f"Firestore storage failed: {e}")
        overall_status = 500

    # --- Overwriting latest value to current data Collection ---
    TARGET_COLLECTION = "current_airquality_data"
    # Use a fixed document ID to ensure overwrite
    FIXED_DOC_ID = "bengaluru_latest_aqi" 
    
    try:
        db.collection(TARGET_COLLECTION).document(FIXED_DOC_ID).set(consolidated_aqi_data)
        print(f"✅ Stored/Overwrote current air quality data in '{TARGET_COLLECTION}' with ID: {FIXED_DOC_ID}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore in '{TARGET_COLLECTION}': {e}")
        error_messages.append(f"Firestore storage failed for latest data: {e}")
        overall_status = 500

    if error_messages:
        return f"❌ Completed with errors: {'; '.join(error_messages)}. Stored partial/full data with ID: {doc_id}", overall_status
    else:
        return f"✅ Successfully fetched and stored consolidated air quality data with ID: {doc_id}", 200
'''


'''v2
import requests
import os
from datetime import datetime, timezone
from google.cloud import firestore

# --- Configuration ---
# Google Cloud Project ID for Firestore
# It's recommended to fetch this from the environment for Cloud Functions
# The 'GCP_PROJECT' environment variable is automatically set by Cloud Functions.
PROJECT_ID = os.getenv('GCP_PROJECT') 
if not PROJECT_ID:
    # Fallback if GCP_PROJECT isn't automatically set (e.g., local testing without gcloud env)
    PROJECT_ID = "cityinsightmaps" # Replace with your actual project ID if not using GCP_PROJECT env var

# OpenWeatherMap API Key - Set this as an environment variable in your Cloud Function
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    print("Error: API_KEY environment variable not set. Please set it in Cloud Function config.")

# Initialize Firestore client globally to reuse connection
# It's good practice to initialize outside the function if possible for performance,
# but also handle potential initialization errors if the env var isn't ready.
db = None
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    print(f"Firestore client initialization failed at global scope: {e}")

# --- Define Important City Points for Bengaluru ---
# You can add more points as needed to cover your definition of "whole city limits"
# Consider major intersections, tech parks, residential hubs, etc.
BENGALURU_LOCATIONS = {
    "City_Centre_Majestic": {"lat": 12.9762, "lon": 77.5713},  # Majestic, Bus Stand/Railway Station area
    "Koramangala": {"lat": 12.9345, "lon": 77.6190},     # Popular residential/commercial area
    "Electronic_City": {"lat": 12.8465, "lon": 77.6631}, # Major tech hub in south
    "Whitefield": {"lat": 12.9698, "lon": 77.7500},      # Major tech hub in east
    "Yelahanka": {"lat": 13.1007, "lon": 77.5750},       # North Bengaluru, near airport road
    "Jayanagar": {"lat": 12.9234, "lon": 77.5870},       # Established residential area
    "Indiranagar": {"lat": 12.9719, "lon": 77.6412},     # Popular commercial/residential
    "Malleshwaram": {"lat": 13.0039, "lon": 77.5683},    # Old Bengaluru, residential
    "Marathahalli": {"lat": 12.9667, "lon": 77.7167}      # Eastern tech corridor
}

# OpenWeatherMap Air Pollution API URL
OPENWEATHER_AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

def get_aqi_category(aqi_value):
    """Maps AQI value to a descriptive category based on OpenWeatherMap's scale."""
    category_map = {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor"
    }
    return category_map.get(aqi_value, "Unknown")

def airquality_handler(request):
    """
    Google Cloud Function to check air quality for a list of important city points
    in Bengaluru using OpenWeatherMap API and store the consolidated response
    as a single JSON record in Firestore.

    Args:
        request (flask.Request): The HTTP request object.
                                 This function is designed to be triggered by HTTP (e.g., Cloud Scheduler).
    Returns:
        tuple: A tuple containing the response message (str) and HTTP status code (int).
    """
    global db # Access the globally initialized Firestore client

    if not API_KEY:
        print("Function exiting due to missing API_KEY.")
        return "❌ Missing API key in environment variables.", 500

    if db is None:
        try: # Try to initialize Firestore client if it failed globally
            db = firestore.Client(project=PROJECT_ID)
            print("Firestore client initialized successfully within function.")
        except Exception as e:
            print(f"Firestore client initialization failed: {e}")
            return "❌ Firestore client could not be initialized. Check logs.", 500

    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # This will be the single JSON record stored in Firestore
    consolidated_aqi_data = {
        "city": "Bengaluru",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "source": "OpenWeatherMap",
        "locations": [] # List to hold data for each point
    }
    
    overall_status = 200
    error_messages = []

    print(f"Starting air quality data fetch for Bengaluru at {time_str}")

    for name, coords in BENGALURU_LOCATIONS.items():
        lat = coords["lat"]
        lon = coords["lon"]
        
        params = {'lat': lat, 'lon': lon, 'appid': API_KEY}

        try:
            response = requests.get(OPENWEATHER_AQI_URL, params=params, timeout=30)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            if "list" not in data or not data["list"]:
                print(f"No air quality data available for {name} ({lat}, {lon}).")
                error_messages.append(f"No data for {name}")
                # Continue to next location, don't fail the whole function
                continue 

            aqi_data = data["list"][0] # Get the current AQI data
            
            location_aqi_record = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "aqi": aqi_data.get("main", {}).get("aqi"),
                "aqi_category": get_aqi_category(aqi_data.get("main", {}).get("aqi")),
                "components": aqi_data.get("components", {}),
                "retrieval_status": "success"
            }
            consolidated_aqi_data["locations"].append(location_aqi_record)
            print(f"Successfully retrieved AQI for {name}.")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching AQI for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as an error if any single call fails
            consolidated_aqi_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })
        except Exception as e:
            error_msg = f"An unexpected error occurred for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500
            consolidated_aqi_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })

    # Generate a unique document ID based on city and timestamp
    doc_id = f"bengaluru_aqi_{time_str}"
    
    try:
        db.collection("bengaluru_air_quality").document(doc_id).set(consolidated_aqi_data)
        print(f"✅ Stored consolidated air quality data with ID: {doc_id}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore: {e}")
        error_messages.append(f"Firestore storage failed: {e}")
        overall_status = 500

    if error_messages:
        return f"❌ Completed with errors: {'; '.join(error_messages)}. Stored partial/full data with ID: {doc_id}", overall_status
    else:
        return f"✅ Successfully fetched and stored consolidated air quality data with ID: {doc_id}", 200
'''



'''v1
import requests
import os
from datetime import datetime, timezone
from google.cloud import firestore

def airquality_handler(request):
    LAT = 12.9716
    LON = 77.5946
    CITY = "Bengaluru"
    API_KEY = os.getenv('API_KEY')  # Set this in Cloud Function's env variables

    if not API_KEY:
        return "❌ Missing API key in environment variables.", 500

    URL = "https://api.openweathermap.org/data/2.5/air_pollution"
    params = {'lat': LAT, 'lon': LON, 'appid': API_KEY}

    response = requests.get(URL, params=params)
    if response.status_code != 200:
        return f"❌ Error fetching air quality data: {response.text}", 500

    data = response.json()
    if "list" not in data or not data["list"]:
        return "❌ No air quality data available.", 500

    aqi_data = data["list"][0]
    now_utc = datetime.now(timezone.utc)
    time_str = now_utc.strftime("%Y%m%d_%H%M%S")
    doc_id = f"{CITY.lower()}_air_{time_str}"

    category_map = {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor"
    }

    transformed = {
        "city": CITY,
        "timestamp": now_utc.isoformat(),
        "lat": LAT,
        "lon": LON,
        "aqi": aqi_data.get("main", {}).get("aqi"),
        "aqi_category": category_map.get(aqi_data.get("main", {}).get("aqi"), "Unknown"),
        "components": aqi_data.get("components", {}),
        "source": "OpenWeatherMap"
    }

    db = firestore.Client(project="cityinsightmaps")
    db.collection("raw_airquality_data").document(doc_id).set(transformed)

    return f"✅ Stored air quality data with ID: {doc_id}", 200
'''