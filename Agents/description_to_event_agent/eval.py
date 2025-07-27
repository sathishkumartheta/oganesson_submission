# eval.py

import vertexai
from vertexai import agent_engines
import json

# Step 1: Init Vertex AI
vertexai.init(
    project="cityinsightmaps",
    location="us-central1"
)

# Step 2: Load the new Agent Engine
agent_engine = agent_engines.get(
    "projects/1092037303200/locations/us-central1/reasoningEngines/6597659104888487936"
)

# Step 3: Create a session
session = agent_engine.create_session(user_id="user_001")
session_id = session["id"]
print(f"✅ Using session ID: {session_id}")

# Step 4: Stream a test query to the agent
print("📡 Querying agent...")
collected_responses = []

for event in agent_engine.stream_query(
    user_id="user_001",
    session_id=session_id,
    message="""
2025-07-23T13:36:46.075890+05:30
Here's a summary of the recent news from Bengaluru:

Bengaluru is expecting patchy rain and mild temperatures around 20.8°C with an 89% chance of precipitation on July 23, 2025. Residents should prepare for continued overcast skies and occasional rain throughout the week.

In concerning news, two women in Bengaluru were victims of a digital arrest scam. Fraudsters, posing as police officers, coerced them into stripping during a fake online examination and tricked them into transferring Rs 58,447. The fraudsters threatened to release nude photos.

On a positive note, tenders have been floated for the construction of two world-class sports complexes in Bengaluru.

The High Court has ordered notice to the Karnataka government regarding the validity of 'Greater Bengaluru'.

A merchant in Bengaluru lost Rs 4.5 lakh to currency exchange fraudsters in a 'Riyal-life trap'.

The 'Panchapeeta' backing for Vijayendra could complicate the power tussle within the BJP.
"""
):
    source = event.get("agent") or event.get("tool") or "root_agent"
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

# Step 5: Output result
print("\n🟢 Structured Output by Agent/Tool:\n")
for item in collected_responses:
    label = f"[{item['source']}]"
    value = item["value"]
    if isinstance(value, (dict, list)):
        print(f"{label} → (JSON output):")
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(f"{label} → {value}\n")
