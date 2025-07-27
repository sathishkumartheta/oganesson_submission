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
