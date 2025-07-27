import os
import requests
from dotenv import load_dotenv

load_dotenv()

Maps_API_KEY = os.getenv('Maps_API_KEY')
if not Maps_API_KEY:
    raise RuntimeError("❌ Maps_API_KEY not set in environment.")

url = "https://routes.googleapis.com/directions/v2:computeRoutes"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": Maps_API_KEY,
    "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters"
}

data = {
    "origin": {
        "location": {
            "latLng": {
                "latitude": 12.9762,
                "longitude": 77.5713
            }
        }
    },
    "destination": {
        "location": {
            "latLng": {
                "latitude": 12.9345,
                "longitude": 77.6190
            }
        }
    },
    "travelMode": "DRIVE",
    "routingPreference": "TRAFFIC_AWARE",  # ✅ FIXED
    "computeAlternativeRoutes": False,
    "languageCode": "en-US",
    "units": "METRIC"
}

response = requests.post(url, headers=headers, json=data)
print("❌ Response content:", response.text)
response.raise_for_status()

route = response.json()["routes"][0]
print("✅ Route fetched successfully:")
print(f"- Distance: {route['distanceMeters']} meters")
print(f"- Duration (with traffic): {route['duration']}")
print(f"- Duration (without traffic): {route['staticDuration']}")
