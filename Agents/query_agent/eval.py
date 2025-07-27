# eval.py — for deployed qa_agent with session-based query

import vertexai
from vertexai import agent_engines

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
query = "Show me traffic updates in Majestic"
print(f"🟢 Query: {query}\n")

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
print("🧠 Agent Output:\n")
print("\n".join(collected))
