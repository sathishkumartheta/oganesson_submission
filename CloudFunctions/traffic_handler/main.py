'''v2'''
import os
import requests
from datetime import datetime
from google.cloud import firestore
import pytz  # 👈 Required for IST timezone handling
from google.cloud import pubsub_v1
import json

# Static location map
BENGALURU_LOCATIONS = {
    "City_Centre_Majestic": {"lat": 12.9762, "lon": 77.5713},
    "Koramangala": {"lat": 12.9345, "lon": 77.6190},
    "Electronic_City": {"lat": 12.8465, "lon": 77.6631},
    "Whitefield": {"lat": 12.9698, "lon": 77.7500},
    "Yelahanka": {"lat": 13.1007, "lon": 77.5750},
    "Jayanagar": {"lat": 12.9234, "lon": 77.5870},
    "Indiranagar": {"lat": 12.9719, "lon": 77.6412},
    "Malleshwaram": {"lat": 13.0039, "lon": 77.5683},
    "Marathahalli": {"lat": 12.9667, "lon": 77.7167}
}

PROJECT_ID = "cityinsightmaps"
Maps_API_KEY = os.getenv("Maps_API_KEY")
if not Maps_API_KEY:
    raise RuntimeError("❌ Maps_API_KEY not set in environment.")

# Pub/Sub Topic ID for Traffic Updates
# IMPORTANT: This should be the actual name of your Pub/Sub topic, e.g., "bengaluru_traffic_updates"
PUBSUB_TOPIC_ID_TRAFFIC = os.getenv('PUBSUB_TOPIC_ID_TRAFFIC')

if not PUBSUB_TOPIC_ID_TRAFFIC:
    print("Warning: PUBSUB_TOPIC_ID_TRAFFIC environment variable not set. Traffic data will NOT be published to Pub/Sub.")


# Initialize Firestore client globally
db = firestore.Client(project=PROJECT_ID)

# Initialize Pub/Sub publisher client globally
pubsub_publisher_client = None
try:
    pubsub_publisher_client = pubsub_v1.PublisherClient()
except Exception as e:
    print(f"Pub/Sub PublisherClient initialization failed at global scope: {e}")

def parse_duration(duration_str):
    try:
        return int(float(duration_str.replace("s", "")))
    except:
        return 0

def traffic_handler(request):
    """
    Google Cloud Function to fetch real-time traffic data for Bengaluru locations
    using Google Maps Routes API, store it in Firestore, and publish it to Pub/Sub.

    Args:
        request (flask.Request): The HTTP request object.
    Returns:
        tuple: A tuple containing the response message (str) and HTTP status code (int).
    """
    global db, pubsub_publisher_client # Access globally initialized clients

    # 🇮🇳 Get timestamp in IST
    ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
    timestamp = ist_now.strftime("%Y%m%d_%H%M%S")

    results = []
    overall_status = 200
    error_messages = []

    print(f"Starting traffic data fetch for Bengaluru at {timestamp}")

    for source_name, source_coords in BENGALURU_LOCATIONS.items():
        for dest_name, dest_coords in BENGALURU_LOCATIONS.items():
            if source_name == dest_name:
                continue

            url = "https://routes.googleapis.com/directions/v2:computeRoutes"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": Maps_API_KEY,
                "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters"
            }

            data = {
                "origin": {"location": {"latLng": {
                    "latitude": source_coords["lat"],
                    "longitude": source_coords["lon"]
                }}},
                "destination": {"location": {"latLng": {
                    "latitude": dest_coords["lat"],
                    "longitude": dest_coords["lon"]
                }}},
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE",
                "computeAlternativeRoutes": False,
                "languageCode": "en-US",
                "units": "METRIC"
            }

            try:
                resp = requests.post(url, headers=headers, json=data)
                resp.raise_for_status()
                route = resp.json()["routes"][0]

                duration = parse_duration(route["duration"])
                static = parse_duration(route["staticDuration"])
                congestion = round(duration / static, 2) if static > 0 else None

                results.append({
                    "source": source_name,
                    "destination": dest_name,
                    "distance_meters": route["distanceMeters"],
                    "duration_seconds": duration,
                    "static_duration_seconds": static,
                    "congestion_factor": congestion,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "source": source_name,
                    "destination": dest_name,
                    "status": "failed",
                    "error_detail": str(e)
                })

    traffic_data = {
        "timestamp": timestamp,
        "city": "Bengaluru",
        "api_provider": "Maps_Routes_REST",
        "routes": results
    }

    # ✅ 1. Store in raw_traffic_data with timestamped doc ID (historical)
    raw_doc_id = f"bengaluru_traffic_matrix_{timestamp}"
    try:
        db.collection("raw_traffic_data").document(raw_doc_id).set(traffic_data)
        print(f"✅ Stored historical traffic data in 'raw_traffic_data' with ID: {raw_doc_id}")
    except Exception as e:
        error_msg = f"❌ Error storing historical traffic data to Firestore: {e}"
        print(error_msg)
        error_messages.append(error_msg)
        overall_status = 500
        
    '''
    # ✅ 2. Clear all docs in current_traffic_data (if this is the desired behavior)
    # Note: Clearing all docs and then writing 'latest' can be inefficient for large collections.
    # If the collection only ever contains one 'latest' doc, a simple overwrite is better.
    # Your original code cleared all, then set 'latest'. I'm keeping your original logic.
    current_ref = db.collection("current_traffic_data")
    try:
        docs_to_delete = current_ref.stream()
        for doc in docs_to_delete:
            doc.reference.delete()
        print("✅ Cleared all existing documents in 'current_traffic_data'.")
    except Exception as e:
        error_msg = f"❌ Error clearing 'current_traffic_data' collection: {e}"
        print(error_msg)
        error_messages.append(error_msg)
        # Don't set overall_status to 500 if clearing fails but write still succeeds
        # This is a judgment call based on desired error handling.
    '''
    # ✅ 3. Store latest data in current_traffic_data (overwrite 'latest' doc)
    current_ref = db.collection("current_traffic_data")
    FIXED_DOC_ID_CURRENT = "latest"
    try:
        current_ref.document(FIXED_DOC_ID_CURRENT).set(traffic_data)
        print(f"✅ Stored/Overwrote latest traffic data in 'current_traffic_data' with ID: {FIXED_DOC_ID_CURRENT}")
    except Exception as e:
        error_msg = f"❌ Error storing latest traffic data to Firestore in 'current_traffic_data': {e}"
        print(error_msg)
        error_messages.append(error_msg)
        overall_status = 500

    # --- Publish to Pub/Sub (NEW) ---
    if pubsub_publisher_client and PUBSUB_TOPIC_ID_TRAFFIC:
        try:
            topic_path = pubsub_publisher_client.topic_path(PROJECT_ID, PUBSUB_TOPIC_ID_TRAFFIC)
            # Convert JSON data to a string, then encode to bytes
            data_str = json.dumps(traffic_data)
            data_bytes = data_str.encode("utf-8")

            future = pubsub_publisher_client.publish(topic_path, data_bytes)
            message_id = future.result() # Blocks until the message is published
            print(f"✅ Published latest Traffic data to Pub/Sub topic '{PUBSUB_TOPIC_ID_TRAFFIC}' with message ID: {message_id}")
        except Exception as e:
            error_msg = f"❌ Error publishing Traffic data to Pub/Sub topic '{PUBSUB_TOPIC_ID_TRAFFIC}': {e}"
            print(error_msg)
            error_messages.append(error_msg)
            overall_status = 500 # Mark overall status as error if Pub/Sub fails
    else:
        if not PUBSUB_TOPIC_ID_TRAFFIC:
            print("Skipping Pub/Sub for Traffic: PUBSUB_TOPIC_ID_TRAFFIC is not set.")
        if not pubsub_publisher_client:
            print("Skipping Pub/Sub for Traffic: Pub/Sub client not initialized.")


    if error_messages:
        return f"❌ Completed with errors: {'; '.join(error_messages)}. Check logs for details.", overall_status
    else:
        return f"✅ Successfully fetched, stored, and published consolidated traffic data.", 200

'''v1
import os
import requests
from datetime import datetime
from google.cloud import firestore
import pytz  # 👈 Required for IST timezone handling

# Static location map
BENGALURU_LOCATIONS = {
    "City_Centre_Majestic": {"lat": 12.9762, "lon": 77.5713},
    "Koramangala": {"lat": 12.9345, "lon": 77.6190},
    "Electronic_City": {"lat": 12.8465, "lon": 77.6631},
    "Whitefield": {"lat": 12.9698, "lon": 77.7500},
    "Yelahanka": {"lat": 13.1007, "lon": 77.5750},
    "Jayanagar": {"lat": 12.9234, "lon": 77.5870},
    "Indiranagar": {"lat": 12.9719, "lon": 77.6412},
    "Malleshwaram": {"lat": 13.0039, "lon": 77.5683},
    "Marathahalli": {"lat": 12.9667, "lon": 77.7167}
}

PROJECT_ID = "cityinsightmaps"
Maps_API_KEY = os.getenv("Maps_API_KEY")
if not Maps_API_KEY:
    raise RuntimeError("❌ Maps_API_KEY not set in environment.")

db = firestore.Client(project=PROJECT_ID)

def parse_duration(duration_str):
    try:
        return int(float(duration_str.replace("s", "")))
    except:
        return 0

def traffic_handler(request):
    # 🇮🇳 Get timestamp in IST
    ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
    timestamp = ist_now.strftime("%Y%m%d_%H%M%S")

    results = []

    for source_name, source_coords in BENGALURU_LOCATIONS.items():
        for dest_name, dest_coords in BENGALURU_LOCATIONS.items():
            if source_name == dest_name:
                continue

            url = "https://routes.googleapis.com/directions/v2:computeRoutes"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": Maps_API_KEY,
                "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters"
            }

            data = {
                "origin": {"location": {"latLng": {
                    "latitude": source_coords["lat"],
                    "longitude": source_coords["lon"]
                }}},
                "destination": {"location": {"latLng": {
                    "latitude": dest_coords["lat"],
                    "longitude": dest_coords["lon"]
                }}},
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE",
                "computeAlternativeRoutes": False,
                "languageCode": "en-US",
                "units": "METRIC"
            }

            try:
                resp = requests.post(url, headers=headers, json=data)
                resp.raise_for_status()
                route = resp.json()["routes"][0]

                duration = parse_duration(route["duration"])
                static = parse_duration(route["staticDuration"])
                congestion = round(duration / static, 2) if static > 0 else None

                results.append({
                    "source": source_name,
                    "destination": dest_name,
                    "distance_meters": route["distanceMeters"],
                    "duration_seconds": duration,
                    "static_duration_seconds": static,
                    "congestion_factor": congestion,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "source": source_name,
                    "destination": dest_name,
                    "status": "failed",
                    "error_detail": str(e)
                })

    traffic_data = {
        "timestamp": timestamp,
        "city": "Bengaluru",
        "api_provider": "Maps_Routes_REST",
        "routes": results
    }

    # ✅ 1. Store in raw_traffic_data with timestamped doc ID
    raw_doc_id = f"bengaluru_traffic_matrix_{timestamp}"
    db.collection("raw_traffic_data").document(raw_doc_id).set(traffic_data)

    # ✅ 2. Clear all docs in current_traffic_data
    current_ref = db.collection("current_traffic_data")
    docs = current_ref.stream()
    for doc in docs:
        doc.reference.delete()

    # ✅ 3. Store latest data in current_traffic_data
    current_ref.document("latest").set(traffic_data)

    return f"✅ Traffic data written: raw={raw_doc_id}, current=latest", 200
'''