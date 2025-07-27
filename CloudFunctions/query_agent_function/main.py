import json
import vertexai
from vertexai import agent_engines
from google.cloud import firestore

# Initialize Vertex AI and Firestore
vertexai.init(project="cityinsightmaps", location="us-central1")
agent_engine = agent_engines.get(
    "projects/1092037303200/locations/us-central1/reasoningEngines/977940826116063232"
)
db = firestore.Client()

def get_latest_prompt():
    docs = db.collection("current_user_prompt").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        return doc.to_dict().get("prompt")
    return None

def get_weather(location_name):
    doc = db.collection("current_weather_data").document("bengaluru_latest_weather").get()
    if doc.exists:
        return next((loc for loc in doc.to_dict().get("locations", []) if loc.get("name") == location_name), None)
    return None

def get_air_quality(location_name):
    doc = db.collection("current_airquality_data").document("bengaluru_latest_aqi").get()
    if doc.exists:
        return next((loc for loc in doc.to_dict().get("locations", []) if loc.get("name") == location_name), None)
    return None

def get_traffic(location_name):
    doc = db.collection("current_traffic_data").document("latest").get()
    if doc.exists:
        routes = doc.to_dict().get("routes", [])
        return [r for r in routes if r.get("source") == location_name]
    return None

def run_agent_session(query):
    session_info = agent_engine.create_session(user_id="test-user")
    session_id = session_info["id"]
    collected = []
    for event in agent_engine.stream_query(user_id="test-user", session_id=session_id, message=query):
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                collected.append(part["text"])
    return "\n".join(collected)

def push_combined_info(location_name: str, intent: str):
    if intent.lower() != "information":
        return "Intent is not 'information'."

    weather_data = get_weather(location_name)
    air_data = get_air_quality(location_name)
    traffic_data = get_traffic(location_name)

    if not (weather_data and air_data and traffic_data):
        return f"Missing data for: {location_name}"

    combined_doc = {
        "location": location_name,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "weather": {
            "temperature": weather_data.get("temperature", {}).get("actual"),
            "feels_like": weather_data.get("temperature", {}).get("feels_like"),
            "humidity": weather_data.get("humidity"),
            "description": weather_data.get("weather", {}).get("description"),
            "wind_speed": weather_data.get("wind", {}).get("speed"),
            "location": location_name
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

    # Clear and update Firestore
    ref = db.collection("current_user_response")
    for doc in ref.stream():
        doc.reference.delete()
    ref.add(combined_doc)

    return f"✅ Combined info for {location_name} inserted."

# ENTRYPOINT for Cloud Function
def generate_city_info(request):
    prompt = get_latest_prompt()
    if not prompt:
        return "❌ No prompt found.", 400

    try:
        agent_output = run_agent_session(prompt)
        parsed = json.loads(agent_output)
        locations = parsed.get("locations", [])
        intent = parsed.get("intent", "information")
        if not locations:
            return "❌ No location found in agent output.", 400
        location_name = locations[0]
        result = push_combined_info(location_name, intent)
        return result, 200
    except Exception as e:
        return f"❌ Error: {str(e)}", 500
