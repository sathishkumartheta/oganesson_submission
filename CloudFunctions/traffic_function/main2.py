import os
import requests
from dotenv import load_dotenv
from time import sleep

load_dotenv()

Maps_API_KEY = os.getenv('Maps_API_KEY')
if not Maps_API_KEY:
    raise RuntimeError("❌ Maps_API_KEY not set in environment.")

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

url = "https://routes.googleapis.com/directions/v2:computeRoutes"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": Maps_API_KEY,
    "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters"
}

def parse_duration(duration_str):
    try:
        return int(float(duration_str.replace("s", "")))
    except:
        return 0

for source_name, source_coords in BENGALURU_LOCATIONS.items():
    for dest_name, dest_coords in BENGALURU_LOCATIONS.items():
        if source_name == dest_name:
            continue

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

        print(f"🚦 {source_name} ➝ {dest_name}")
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            route = response.json()["routes"][0]

            duration = parse_duration(route["duration"])
            static_duration = parse_duration(route["staticDuration"])
            congestion = round(duration / static_duration, 2) if static_duration > 0 else "N/A"

            print(f"✅ Distance: {route['distanceMeters']} m | Duration: {duration}s | Static: {static_duration}s | Congestion: {congestion}")
        except Exception as e:
            print(f"❌ Failed to get route: {e}")
        
        print("-" * 70)
        sleep(0.25)  # Small delay to avoid rate limits
