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
PROJECT_ID = os.getenv('GCP_PROJECT')
if not PROJECT_ID:
    PROJECT_ID = "cityinsightmaps" # Fallback, replace if your project ID is different

# OpenWeatherMap API Key - Set this as an environment variable in your Cloud Function
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    print("Error: API_KEY environment variable not set. Please set it in Cloud Function config.")

# Pub/Sub Topic ID for Weather Updates
# IMPORTANT: This should be the actual name of your Pub/Sub topic, e.g., "bengaluru_weather_updates"
PUBSUB_TOPIC_ID_WEATHER = os.getenv('PUBSUB_TOPIC_ID_WEATHER')

if not PUBSUB_TOPIC_ID_WEATHER:
    print("Warning: PUBSUB_TOPIC_ID_WEATHER environment variable not set. Weather data will NOT be published to Pub/Sub.")


# Initialize Firestore client globally to reuse connection
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
# This list should be identical to the one used in your airquality_handler
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

# OpenWeatherMap Current Weather API URL (using lat/lon)
OPENWEATHER_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

def weather_handler(request):
    """
    Google Cloud Function to check real-time weather for a list of important city points
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
        try: # Try to re-initialize Firestore client if it failed globally
            db = firestore.Client(project=PROJECT_ID)
            print("Firestore client initialized successfully within function.")
        except Exception as e:
            print(f"Firestore client initialization failed: {e}")
            return "❌ Firestore client could not be initialized. Check logs.", 500
    
    # 🇮🇳 Get timestamp in IST
    ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
    timestamp = ist_now.strftime("%Y%m%d_%H%M%S")
    
    # This will be the single JSON record stored in Firestore
    consolidated_weather_data = {
        "city": "Bengaluru", # General city for the overall record
        "timestamp": timestamp,
        "source": "OpenWeatherMap",
        "locations": [] # List to hold weather data for each point
    }
    
    overall_status = 200
    error_messages = []

    print(f"Starting weather data fetch for Bengaluru at {timestamp}")

    for name, coords in BENGALURU_LOCATIONS.items():
        lat = coords["lat"]
        lon = coords["lon"]
        
        # Parameters for OpenWeatherMap Current Weather API
        params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY,
            'units': 'metric' # For Celsius
        }

        try:
            response = requests.get(OPENWEATHER_WEATHER_URL, params=params, timeout=30)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            # Extract and transform relevant weather data for the current location
            location_weather_record = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "weather": {
                    "main": data.get("weather", [{}])[0].get("main"),
                    "description": data.get("weather", [{}])[0].get("description"),
                    "icon": data.get("weather", [{}])[0].get("icon")
                },
                "temperature": {
                    "actual": data.get("main", {}).get("temp"),
                    "feels_like": data.get("main", {}).get("feels_like"),
                    "humidity": data.get("main", {}).get("humidity")
                },
                "wind": {
                    "speed": data.get("wind", {}).get("speed"),
                    "gust": data.get("wind", {}).get("gust")
                },
                "cloud_coverage": data.get("clouds", {}).get("all"),                
                "sunrise": data.get("sys", {}).get("sunrise"),
                "sunset": data.get("sys", {}).get("sunset"),
                "retrieval_status": "success"
            }
            consolidated_weather_data["locations"].append(location_weather_record)
            print(f"Successfully retrieved weather for {name}.")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching weather for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as an error if any single call fails
            consolidated_weather_data["locations"].append({
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
            consolidated_weather_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })

    # --- Store historical weather data (as per your v3 code) ---
    # This creates a new document for each run with a timestamped ID.
    historical_doc_id = f"bengaluru_weather_{timestamp}"
    try:
        db.collection("bengaluru_weather_data").document(historical_doc_id).set(consolidated_weather_data)
        print(f"✅ Stored historical weather data with ID: {historical_doc_id}")
    except Exception as e:
        print(f"❌ Error storing historical data to Firestore: {e}")
        error_messages.append(f"Firestore historical storage failed: {e}")
        overall_status = 500


    # --- Overwrite latest weather data to current_weather_data Collection ---
    TARGET_COLLECTION_CURRENT = "current_weather_data"
    FIXED_DOC_ID_CURRENT = "bengaluru_latest_weather" 
    
    try:
        db.collection(TARGET_COLLECTION_CURRENT).document(FIXED_DOC_ID_CURRENT).set(consolidated_weather_data)
        print(f"✅ Stored/Overwrote latest weather data in '{TARGET_COLLECTION_CURRENT}' with ID: {FIXED_DOC_ID_CURRENT}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore in '{TARGET_COLLECTION_CURRENT}': {e}")
        error_messages.append(f"Firestore storage failed for latest data: {e}")
        overall_status = 500

    # --- Publish to Pub/Sub ---
    if pubsub_publisher_client and PUBSUB_TOPIC_ID_WEATHER:
        try:
            topic_path = pubsub_publisher_client.topic_path(PROJECT_ID, PUBSUB_TOPIC_ID_WEATHER)
            # Convert JSON data to a string, then encode to bytes
            data_str = json.dumps(consolidated_weather_data)
            data_bytes = data_str.encode("utf-8")

            future = pubsub_publisher_client.publish(topic_path, data_bytes)
            message_id = future.result() # Blocks until the message is published
            print(f"✅ Published latest Weather data to Pub/Sub topic '{PUBSUB_TOPIC_ID_WEATHER}' with message ID: {message_id}")
        except Exception as e:
            error_msg = f"❌ Error publishing Weather data to Pub/Sub topic '{PUBSUB_TOPIC_ID_WEATHER}': {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as error if Pub/Sub fails
    else:
        if not PUBSUB_TOPIC_ID_WEATHER:
            print("Skipping Pub/Sub for Weather: PUBSUB_TOPIC_ID_WEATHER is not set.")
        if not pubsub_publisher_client:
            print("Skipping Pub/Sub for Weather: Pub/Sub client not initialized.")


    if error_messages:
        return f"❌ Completed with errors: {'; '.join(error_messages)}. Stored partial/full data with ID: {historical_doc_id}", overall_status
    else:
        return f"✅ Successfully fetched, stored consolidated weather data with ID: {historical_doc_id} and published latest weather data.", 200


        
'''v3
import requests
import os
from datetime import datetime, timezone
from google.cloud import firestore

# --- Configuration ---
# Google Cloud Project ID for Firestore
PROJECT_ID = os.getenv('GCP_PROJECT')
if not PROJECT_ID:
    PROJECT_ID = "cityinsightmaps" # Fallback, replace if your project ID is different

# OpenWeatherMap API Key - Set this as an environment variable in your Cloud Function
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    print("Error: API_KEY environment variable not set. Please set it in Cloud Function config.")

# Initialize Firestore client globally to reuse connection
db = None
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    print(f"Firestore client initialization failed at global scope: {e}")

# --- Define Important City Points for Bengaluru ---
# This list should be identical to the one used in your airquality_handler
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

# OpenWeatherMap Current Weather API URL (using lat/lon)
OPENWEATHER_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

def weather_handler(request):
    """
    Google Cloud Function to check real-time weather for a list of important city points
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
        try: # Try to re-initialize Firestore client if it failed globally
            db = firestore.Client(project=PROJECT_ID)
            print("Firestore client initialized successfully within function.")
        except Exception as e:
            print(f"Firestore client initialization failed: {e}")
            return "❌ Firestore client could not be initialized. Check logs.", 500

    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # This will be the single JSON record stored in Firestore
    consolidated_weather_data = {
        "city": "Bengaluru", # General city for the overall record
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "source": "OpenWeatherMap",
        "locations": [] # List to hold weather data for each point
    }
    
    overall_status = 200
    error_messages = []

    print(f"Starting weather data fetch for Bengaluru at {time_str}")

    for name, coords in BENGALURU_LOCATIONS.items():
        lat = coords["lat"]
        lon = coords["lon"]
        
        # Parameters for OpenWeatherMap Current Weather API
        params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY,
            'units': 'metric' # For Celsius
        }

        try:
            response = requests.get(OPENWEATHER_WEATHER_URL, params=params, timeout=30)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            # Extract and transform relevant weather data for the current location
            location_weather_record = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "weather": {
                    "main": data.get("weather", [{}])[0].get("main"),
                    "description": data.get("weather", [{}])[0].get("description"),
                    "icon": data.get("weather", [{}])[0].get("icon")
                },
                "temperature": {
                    "actual": data.get("main", {}).get("temp"),
                    "feels_like": data.get("main", {}).get("feels_like"),
                    "humidity": data.get("main", {}).get("humidity")
                },
                "wind": {
                    "speed": data.get("wind", {}).get("speed"),
                    "gust": data.get("wind", {}).get("gust")
                },
                "cloud_coverage": data.get("clouds", {}).get("all"),                
                "sunrise": data.get("sys", {}).get("sunrise"),
                "sunset": data.get("sys", {}).get("sunset"),
                "retrieval_status": "success"
            }
            consolidated_weather_data["locations"].append(location_weather_record)
            print(f"Successfully retrieved weather for {name}.")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching weather for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as an error if any single call fails
            consolidated_weather_data["locations"].append({
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
            consolidated_weather_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })

    # Generate a unique document ID based on city and timestamp
    doc_id = f"bengaluru_weather_{time_str}"
    
    try:
        db.collection("bengaluru_weather_data").document(doc_id).set(consolidated_weather_data)
        print(f"✅ Stored consolidated weather data with ID: {doc_id}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore: {e}")
        error_messages.append(f"Firestore storage failed: {e}")
        overall_status = 500

    # --- Overwrite latest weather data to current data Collection ---
    TARGET_COLLECTION = "current_weather_data"
    # Use a fixed document ID to ensure overwrite
    FIXED_DOC_ID = "bengaluru_latest_weather" 
    
    try:
        db.collection(TARGET_COLLECTION).document(FIXED_DOC_ID).set(consolidated_weather_data)
        print(f"✅ Stored/Overwrote latest weather data in '{TARGET_COLLECTION}' with ID: {FIXED_DOC_ID}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore in '{TARGET_COLLECTION}': {e}")
        error_messages.append(f"Firestore storage failed for latest data: {e}")
        overall_status = 500

    if error_messages:
        return f"❌ Completed with errors: {'; '.join(error_messages)}. Stored partial/full data with ID: {doc_id}", overall_status
    else:
        return f"✅ Successfully fetched and stored consolidated weather data with ID: {doc_id}", 200
'''

'''v2
import requests
import os
from datetime import datetime, timezone
from google.cloud import firestore

# --- Configuration ---
# Google Cloud Project ID for Firestore
PROJECT_ID = os.getenv('GCP_PROJECT')
if not PROJECT_ID:
    PROJECT_ID = "cityinsightmaps" # Fallback, replace if your project ID is different

# OpenWeatherMap API Key - Set this as an environment variable in your Cloud Function
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    print("Error: API_KEY environment variable not set. Please set it in Cloud Function config.")

# Initialize Firestore client globally to reuse connection
db = None
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    print(f"Firestore client initialization failed at global scope: {e}")

# --- Define Important City Points for Bengaluru ---
# This list should be identical to the one used in your airquality_handler
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

# OpenWeatherMap Current Weather API URL (using lat/lon)
OPENWEATHER_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

def weather_handler(request):
    """
    Google Cloud Function to check real-time weather for a list of important city points
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
        try: # Try to re-initialize Firestore client if it failed globally
            db = firestore.Client(project=PROJECT_ID)
            print("Firestore client initialized successfully within function.")
        except Exception as e:
            print(f"Firestore client initialization failed: {e}")
            return "❌ Firestore client could not be initialized. Check logs.", 500

    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # This will be the single JSON record stored in Firestore
    consolidated_weather_data = {
        "city": "Bengaluru", # General city for the overall record
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "source": "OpenWeatherMap",
        "locations": [] # List to hold weather data for each point
    }
    
    overall_status = 200
    error_messages = []

    print(f"Starting weather data fetch for Bengaluru at {time_str}")

    for name, coords in BENGALURU_LOCATIONS.items():
        lat = coords["lat"]
        lon = coords["lon"]
        
        # Parameters for OpenWeatherMap Current Weather API
        params = {
            'lat': lat,
            'lon': lon,
            'appid': API_KEY,
            'units': 'metric' # For Celsius
        }

        try:
            response = requests.get(OPENWEATHER_WEATHER_URL, params=params, timeout=30)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            # Extract and transform relevant weather data for the current location
            location_weather_record = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "weather": {
                    "main": data.get("weather", [{}])[0].get("main"),
                    "description": data.get("weather", [{}])[0].get("description"),
                    "icon": data.get("weather", [{}])[0].get("icon")
                },
                "temperature": {
                    "actual": data.get("main", {}).get("temp"),
                    "feels_like": data.get("main", {}).get("feels_like"),
                    "humidity": data.get("main", {}).get("humidity")
                },
                "wind": {
                    "speed": data.get("wind", {}).get("speed"),
                    "gust": data.get("wind", {}).get("gust")
                },
                "cloud_coverage": data.get("clouds", {}).get("all"),                
                "sunrise": data.get("sys", {}).get("sunrise"),
                "sunset": data.get("sys", {}).get("sunset"),
                "retrieval_status": "success"
            }
            consolidated_weather_data["locations"].append(location_weather_record)
            print(f"Successfully retrieved weather for {name}.")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching weather for {name} ({lat}, {lon}): {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as an error if any single call fails
            consolidated_weather_data["locations"].append({
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
            consolidated_weather_data["locations"].append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "retrieval_status": "failed",
                "error_detail": str(e)
            })

    # Generate a unique document ID based on city and timestamp
    doc_id = f"bengaluru_weather_{time_str}"
    
    try:
        db.collection("bengaluru_weather_data").document(doc_id).set(consolidated_weather_data)
        print(f"✅ Stored consolidated weather data with ID: {doc_id}")
    except Exception as e:
        print(f"❌ Error storing data to Firestore: {e}")
        error_messages.append(f"Firestore storage failed: {e}")
        overall_status = 500

    if error_messages:
        return f"❌ Completed with errors: {'; '.join(error_messages)}. Stored partial/full data with ID: {doc_id}", overall_status
    else:
        return f"✅ Successfully fetched and stored consolidated weather data with ID: {doc_id}", 200
'''


'''v1
import requests
from google.cloud import firestore
import os
from datetime import datetime

def weather_handler(request):
    CITY = "Bengaluru"
    API_KEY = os.getenv('API_KEY')  # Set this as environment variable in GCF

    URL = "https://api.openweathermap.org/data/2.5/weather"
    params = {'q': CITY, 'appid': API_KEY, 'units': 'metric'}

    response = requests.get(URL, params=params)
    if response.status_code != 200:
        return f"Error fetching weather: {response.text}", 500

    data = response.json()

    # Format current time for unique document ID
    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_id = f"{CITY.lower()}_{time_str}"

    # Transform and store in Firestore
    transformed = {
        "city": data.get("name"),
        "country": data.get("sys", {}).get("country"),
        "timestamp": data.get("dt"),
        "lat": data.get("coord", {}).get("lat"),
        "lon": data.get("coord", {}).get("lon"),
        "weather": {
            "main": data.get("weather", [{}])[0].get("main"),
            "description": data.get("weather", [{}])[0].get("description"),
            "icon": data.get("weather", [{}])[0].get("icon")
        },
        "temperature": {
            "actual": data.get("main", {}).get("temp"),
            "feels_like": data.get("main", {}).get("feels_like"),
            "humidity": data.get("main", {}).get("humidity")
        },
        "wind": {
            "speed": data.get("wind", {}).get("speed"),
            "gust": data.get("wind", {}).get("gust")
        },
        "cloud_coverage": data.get("clouds", {}).get("all"),
        "sunrise": data.get("sys", {}).get("sunrise"),
        "sunset": data.get("sys", {}).get("sunset")
    }

    db = firestore.Client("cityinsightmaps")
    db.collection("raw_weather_data").document(doc_id).set(transformed)
    return f"✅ Stored weather data with ID: {doc_id}", 200
'''