import time
import json
import re
from typing import Dict, Union, List, Optional
from vertexai.generative_models import GenerativeModel
import vertexai
from google.api_core.exceptions import ResourceExhausted

# Initialize Vertex AI
vertexai.init(project="cityinsightmaps", location="asia-south1")
model = GenerativeModel("gemini-1.5-flash")

def classify_map_query(query: str) -> Dict[str, Union[str, List[str], Optional[str]]]:
    """Classify user query as information, navigation, or other; extract relevant locations."""
    
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

    def classify_intent() -> str:
        prompt = f"""
You are an intent classifier for a city map assistant.

Classify this query as one of:
- "information" (traffic, events, weather, etc.)
- "navigation" (directions, routes)
- "other" (general queries)

Respond with one word only.

Query: "{query}"
"""
        return ask_gemini(prompt).lower()

    def extract_locations() -> List[str]:
        prompt = f"""
Extract all location names mentioned in this information-related query.

Query: "{query}"

Respond ONLY as a valid Python list of strings like:
["KR Puram", "Hebbal"]
"""
        response = ask_gemini(prompt)
        try:
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            return json.loads(match.group(0).replace("'", '"')) if match else []
        except Exception as e:
            print("⚠️ Location parse failed:", e)
            return []

    def extract_route() -> Dict[str, Optional[str]]:
        prompt = f"""
Extract source and destination locations from the following navigation query.

Query: "{query}"

If only one location is found, use it as destination and source should be null.

Respond ONLY in this format:
{{"source": "Place A", "destination": "Place B"}}
"""
        response = ask_gemini(prompt)
        try:
            match = re.search(r'\{.*?\}', response, re.DOTALL)
            return json.loads(match.group(0).replace("'", '"')) if match else {}
        except Exception as e:
            print("⚠️ Route parse failed:", e)
            return {}

    # 🔁 Pipeline logic
    intent = classify_intent()

    if intent == "information":
        return {"intent": "information", "locations": extract_locations()}
    elif intent == "navigation":
        return {"intent": "navigation", **extract_route()}
    else:
        return {"intent": "other", "message": "This query is not handled by the system."}
if __name__ == "__main__":
    test_queries = [
        "Show me traffic updates in KR Puram and Hebbal",
        "Take me from BTM Layout to Indiranagar",
        "Is there any water logging in Rajajinagar?",
        "Give me directions to MG Road",
        "What's the air quality like in Whitefield?",
        "Tell me a joke"
    ]

    for query in test_queries:
        print(f"\n🟢 Query: {query}")
        try:
            output = classify_map_query(query)
            print("🧠 Output:", output)
        except Exception as e:
            print("❌ Error:", e)
