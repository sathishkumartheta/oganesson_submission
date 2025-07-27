from vertexai.generative_models import GenerativeModel
import vertexai

# Init Gemini
vertexai.init(project="cityinsightmaps", location="asia-south1")
model = GenerativeModel("gemini-1.5-flash")

def run_map_query(query: str):
    """Prompt Gemini with a map query and print raw response."""
    prompt = f"""
You are a city map assistant. A user provides a free-text query.

1. Classify the intent as:
   - "information"
   - "navigation"
   - "other"

2. Based on the intent, extract:
   - For information: a list of locations
   - For navigation: source and destination
   - For other: fallback message

Respond in JSON format only.

User query: "{query}"
"""
    response = model.generate_content(prompt)
    print(response.text.strip())

# Example
if __name__ == "__main__":
    run_map_query("Take me from Jayanagar to Majestic")
