import time
import json
import re
from vertexai.generative_models import GenerativeModel
import vertexai
from google.api_core.exceptions import ResourceExhausted

# -----------------------------
# 🔧 Vertex AI Init
# -----------------------------
vertexai.init(project="cityinsightmaps", location="asia-south1")
model = GenerativeModel("gemini-2.5-flash")

# -----------------------------
# 💬 Gemini Request Helper
# -----------------------------
def ask_gemini(prompt: str, max_tokens: int = 512) -> str:
    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"max_output_tokens": max_tokens}
            )
            return response.text.strip()
        except ResourceExhausted:
            print(f"⚠️ Retry {attempt+1}/3: Resource exhausted. Backing off...")
            time.sleep(2 ** attempt)
    raise RuntimeError("❌ Gemini failed after 3 retries.")

# -----------------------------
# 🧠 Single-call Map QA Tool
# -----------------------------
def classify_map_query(query: str) -> dict:
    """Single-call Gemini function to classify map query and extract location info."""

    prompt = f"""
You are a city map assistant. The user gives a free-text query. Your job is to:

1. Classify it as one of:
   - "information" (traffic, weather, air quality, etc.)
   - "navigation" (route or directions)
   - "other" (general or unrelated query)

2. Extract relevant information based on the intent.

Return ONLY one of the following JSON objects:

🛈 For information intent:
{{
  "intent": "information",
  "locations": ["Location1", "Location2"]
}}

🧭 For navigation intent:
{{
  "intent": "navigation",
  "source": "Starting Point",
  "destination": "Ending Point"
}}

🛑 For other/general:
{{
  "intent": "other",
  "message": "This query is not handled by the system."
}}

Query: "{query}"

Respond with only valid JSON.
"""

    try:
        response = ask_gemini(prompt)
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            json_str = match.group(0).replace("'", '"')
            return json.loads(json_str)
        return {"intent": "other", "message": "Could not parse Gemini output."}
    except Exception as e:
        print("❌ Failed to parse Gemini output:", e)
        return {"intent": "error", "message": str(e)}

# -----------------------------
# 🧪 Test Runner
# -----------------------------
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
