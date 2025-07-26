# eval.py

import vertexai
from vertexai import agent_engines
from google.cloud import firestore
from datetime import datetime

# Step 1: Initialize Vertex AI and Firestore
vertexai.init(project="cityinsightmaps", location="us-central1")
db = firestore.Client(project="cityinsightmaps")

# Step 2: Load your deployed agent engine
agent_engine = agent_engines.get(
    "projects/cityinsightmaps/locations/us-central1/reasoningEngines/1031984021644509184"
)

# Step 3: Run the mood map query
print("💬 Asking the agent to generate the mood map for Bengaluru...\n")
collected_text = []

for event in agent_engine.stream_query(
    user_id="test_mood_user",
    message="Generate the mood map for Bengaluru localities today."
):
    source = event.get("agent") or event.get("tool") or event.get("name", "root_agent")
    content = event.get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        if "text" in part:
            collected_text.append(part["text"])

# Combine response into one string
final_mood_map = "\n".join(collected_text)

# Step 4: Save to Firestore
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
doc_ref = db.collection("raw_mood_data").document(timestamp)

doc_ref.set({
    "timestamp": timestamp,
    "mood_map": final_mood_map
})

print("\n✅ Mood map stored in Firestore collection 'raw_mood_data'")
print(f"🕒 Document ID: {timestamp}")
print("\n🟢 Agent Response:\n")
print(final_mood_map)
