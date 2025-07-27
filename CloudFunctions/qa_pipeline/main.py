import time
import json
import re
from vertexai.generative_models import GenerativeModel
import vertexai
from google.api_core.exceptions import ResourceExhausted

# Initialize Vertex AI
vertexai.init(project="cityinsightmaps", location="asia-south1")
model = GenerativeModel("gemini-2.5-flash")

# ------------------------------
# 💬 Gemini Helper with Retry
# ------------------------------
def ask_gemini(prompt: str, max_tokens: int = 256) -> str:
    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"max_output_tokens": max_tokens}
            )
            return response.text.strip()
        except ResourceExhausted:
            print(f"⚠️ Retry {attempt+1}/3: Resource exhausted.")
            time.sleep(2 ** attempt)
    raise RuntimeError("❌ Gemini failed after 3 retries.")

# ------------------------------
# 🔍 Intent Classification
# ------------------------------
def classify_intent(query: str) -> str:
    prompt = f"""
You are an intent classifier for a city map assistant.

Classify this query as one of:
- "information" (for traffic, events, weather, etc.)
- "navigation" (for directions or routes)
- "other" (for general questions)

Respond with one word: information, navigation, or other.

Query: "{query}"
"""
    return ask_gemini(prompt).lower()

# ------------------------------
# 📍 Extract Locations (Info)
# ------------------------------
def extract_locations(query: str) -> list[str]:
    prompt = f"""
Extract all location names mentioned in this information-related query.

Query: "{query}"

Respond ONLY as a valid Python list of strings like:
["KR Puram", "Hebbal"]
"""
    response = ask_gemini(prompt)
    try:
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            return json.loads(match.group(0).replace("'", '"'))
        return []
    except Exception as e:
        print("⚠️ Failed to parse locations:", e)
        return []

# ------------------------------
# 🗺️ Extract Route (Nav)
# ------------------------------
def extract_route(query: str) -> dict:
    prompt = f"""
Extract source and destination locations from the following navigation query.

Query: "{query}"

If only one location is found, set destination, and source as null.

Respond ONLY in this format:
{{"source": "Place A", "destination": "Place B"}}
"""
    response = ask_gemini(prompt)
    try:
        match = re.search(r'\{.*?\}', response, re.DOTALL)
        if match:
            return json.loads(match.group(0).replace("'", '"'))
        return {}
    except Exception as e:
        print("⚠️ Failed to parse route:", e)
        return {}

# ------------------------------
# 🚀 Unified Query Processor
# ------------------------------
def process_query(query: str) -> dict:
    intent = classify_intent(query)

    if intent == "information":
        locations = extract_locations(query)
        return {"intent": "information", "locations": locations}

    elif intent == "navigation":
        route = extract_route(query)
        return {"intent": "navigation", **route}

    else:
        return {"intent": "other", "message": "This query is not handled by the system."}

# ------------------------------
# 🧪 Sample Queries
# ------------------------------
if __name__ == "__main__":
    queries = [
        "Show me traffic updates in KR Puram and Hebbal",
        "Take me from BTM Layout to Indiranagar",
        "Tell me a joke"
    ]

    for q in queries:
        print(f"\n🟢 Query: {q}")
        print("🧠 Output:", process_query(q))
