# eval_predictive_agent.py

import vertexai
from vertexai import agent_engines
import json

# Step 1: Initialize Vertex AI
vertexai.init(
    project="cityinsightmaps",
    location="us-central1"
)

# Step 2: Reference the deployed AgentEngine
agent_engine = agent_engines.get(
    "projects/1092037303200/locations/us-central1/reasoningEngines/1607881823994511360"
)



# Step 3: Create a new session
session = agent_engine.create_session(user_id="test_user_deployed")
session_id = session["id"]
print(f"✅ Using session ID: {session_id}")

# Step 4: Send query and stream response
print("💬 Querying deployed predictive agent...\n")
collected_responses = []

for event in agent_engine.stream_query(
    user_id="test_user_deployed",
    session_id=session_id,
    message="Give me the predictive commentary for Bengaluru today."
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
        elif "function_response" in part:
            result = part["function_response"].get("response", {}).get("result")
            try:
                parsed = json.loads(result.replace("'", '"')) if isinstance(result, str) else result
            except Exception:
                parsed = result
            collected_responses.append({
                "source": source,
                "type": "function_response",
                "value": parsed
            })
        elif "function_call" in part:
            collected_responses.append({
                "source": source,
                "type": "function_call",
                "value": part["function_call"]
            })

# Step 5: Pretty-print final output
print("\n🟢 Structured Output by Agent/Tool:\n")
for item in collected_responses:
    label = f"[{item['source']} - {item['type']}]"
    value = item["value"]
    if isinstance(value, (dict, list)):
        print(f"{label} → (JSON):")
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(f"{label} → {value}\n")
