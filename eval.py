# eval.py

import vertexai
from vertexai import agent_engines

# Step 1: Initialize Vertex AI
vertexai.init(
    project="cityinsightmaps",
    location="us-central1"
)

# Step 2: Load your deployed agent engine
agent_engine = agent_engines.get(
    "projects/cityinsightmaps/locations/us-central1/reasoningEngines/1031984021644509184"
)

# Step 3: Run a test query
print("💬 Asking the agent to generate the mood map for Bengaluru...\n")
collected_responses = []

for event in agent_engine.stream_query(
    user_id="test_mood_user",
    message="Generate the mood map for Bengaluru localities today."
):
    source = event.get("agent") or event.get("tool") or event.get("name", "root_agent")
    content = event.get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        if "text" in part:
            collected_responses.append({
                "source": source,
                "type": "text",
                "value": part["text"]
            })

# Step 4: Display final response
print("\n🟢 Agent Response:\n")
for item in collected_responses:
    print(f"[{item['source']} - {item['type']}] →\n{item['value']}\n")
