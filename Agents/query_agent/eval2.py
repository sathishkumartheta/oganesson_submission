# eval.py — for deployed qa_agent with session-based query

import vertexai
from vertexai import agent_engines
import json  # ✅ Added for parsing JSON-like output
from google.cloud import firestore
# Step 1: Initialize Vertex AI
vertexai.init(project="cityinsightmaps", location="us-central1")

# Step 2: Connect to your deployed agent
agent_engine = agent_engines.get(
    "projects/1092037303200/locations/us-central1/reasoningEngines/977940826116063232"
)

# Step 3: Create session
session_info = agent_engine.create_session(user_id="test-user")
session_id = session_info["id"]

# Step 4: Send message using stream_query
# Step 4: Fetch latest prompt from Firestore
db = firestore.Client()
prompt_docs = db.collection("current_user_prompt").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()

query = None
for doc in prompt_docs:
    query = doc.to_dict().get("prompt")

if not query:
    raise ValueError("❌ No user prompt found in Firestore!")

print(f"🟢 Query from Firestore: {query}\n")

collected = []
for event in agent_engine.stream_query(
    user_id="test-user",
    session_id=session_id,
    message=query
):
    content = event.get("content", {})
    parts = content.get("parts", [])
    for part in parts:
        if "text" in part:
            collected.append(part["text"])

# Step 5: Print final output
final_output = "\n".join(collected)
print("🧠 Agent Output:\n")
print(final_output)

parsed = json.loads(final_output)
locations = parsed.get("locations", [])
transformed_ids = [f"{loc}" for loc in locations]

# Step 6: Extract locations (if present) and convert them
#try:
#    parsed = json.loads(final_output)
#    locations = parsed.get("locations", [])
#    transformed_ids = [f"City_Centre_{loc}" for loc in locations]
#    print("\n📍 Transformed document IDs for Firestore lookup:")
#    print(transformed_ids)
#except Exception as e:
#    print("\n⚠️ Could not parse agent output as JSON. Error:")
#    print(e)
location_name=transformed_ids[0]

from google.cloud import firestore

def get_weather_info_from_array(location_name: str):
    db = firestore.Client()
    doc_ref = db.collection("current_weather_data").document("bengaluru_latest_weather")
    doc = doc_ref.get()

    if not doc.exists:
        print("❌ Document not found.")
        return

    data = doc.to_dict()
    locations = data.get("locations", [])

    for loc in locations:
        if loc.get("name") == location_name:
            print(f"\n📍 Weather Summary for {loc['name']}:")
            print(f"☁️ Condition: {loc['weather']['main']} ({loc['weather']['description']})")
            print(f"🌡️ Temperature: {loc['temperature']['actual']}°C (Feels like {loc['temperature']['feels_like']}°C)")
            print(f"💧 Humidity: {loc['temperature']['humidity']}%")
            print(f"💨 Wind: {loc['wind']['speed']} m/s, Gusts up to {loc['wind']['gust']} m/s")
            print(f"📡 Cloud Coverage: {loc['cloud_coverage']}%")
            print(f"🌅 Sunrise: {loc['sunrise']}")
            print(f"🌇 Sunset: {loc['sunset']}")
            return

    print(f"❌ Location '{location_name}' not found in current_weather_data.")

get_weather_info_from_array(location_name)


from google.cloud import firestore

def get_air_quality(location_name: str):
    """
    Fetches air quality data for a given location from the 'locations' array
    inside the 'bengaluru_latest_aqi' document in 'current_airquality_data' collection.
    """
    db = firestore.Client()
    doc_ref = db.collection("current_airquality_data").document("bengaluru_latest_aqi")
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        for loc in data.get("locations", []):
            if loc.get("name") == location_name:
                return loc  # matched location object
    return None


    return None  # If no matching document found

print(get_air_quality(location_name))

from google.cloud import firestore

def push_combined_city_info(location_name: str, intent: str):
    """
    Combines weather, air quality, and traffic data into one document if intent is 'information'.
    Writes to `current_city_info` collection in Firestore.
    """
    if intent.lower() != "information":
        print("❌ Intent is not 'information'. Skipping Firestore write.")
        return

    db = firestore.Client()

    # --- Get Weather ---
    weather_doc = db.collection("current_weather_data").document("bengaluru_latest_weather").get()
    weather_data = next((loc for loc in weather_doc.to_dict().get("locations", []) if loc.get("name") == location_name), None) if weather_doc.exists else None

    # --- Get Air Quality ---
    air_doc = db.collection("current_airquality_data").document("bengaluru_latest_aqi").get()
    air_data = next((loc for loc in air_doc.to_dict().get("locations", []) if loc.get("name") == location_name), None) if air_doc.exists else None

    # --- Get Traffic ---
    traffic_doc = db.collection("current_traffic_data").document("latest").get()
    traffic_data = None
    if traffic_doc.exists:
        traffic_routes = traffic_doc.to_dict().get("routes", [])
        traffic_data = [route for route in traffic_routes if route.get("source") == location_name]

    if not (weather_data and air_data and traffic_data):
        print("❌ Missing one or more data sources for:", location_name)
        return

    # --- Construct Combined Document ---
    combined_doc = {
        "location": location_name,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "weather": {
            "temperature": weather_data.get("temperature", {}).get("actual"),
            "feels_like": weather_data.get("temperature", {}).get("feels_like"),
            "humidity": weather_data.get("humidity"),
            "description": weather_data.get("weather", {}).get("description"),
            "wind_speed": weather_data.get("wind", {}).get("speed"),
        },
        "air_quality": {
            "aqi": air_data.get("aqi"),
            "aqi_category": air_data.get("aqi_category"),
            "co": air_data.get("components", {}).get("co"),
            "no2": air_data.get("components", {}).get("no2"),
            "pm2_5": air_data.get("components", {}).get("pm2_5"),
        },
        "traffic": [
            {
                "source": route["source"],
                "destination": route["destination"],
                "congestion_factor": route.get("congestion_factor"),
                "duration_seconds": route.get("duration_seconds"),
                "static_duration_seconds": route.get("static_duration_seconds"),
                "distance_meters": route.get("distance_meters")
            }
            for route in traffic_data
        ]
    }

    user_response_ref = db.collection("current_user_response")
    docs = user_response_ref.stream()
    for doc in docs:
        doc.reference.delete()

    # --- Add new document ---
    user_response_ref.add(combined_doc)
    print("✅ Cleared `current_user_response` and inserted new data.")

push_combined_city_info(location_name,"information")
