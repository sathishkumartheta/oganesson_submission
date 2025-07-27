import json
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
import vertexai
from vertexai import agent_engines
import pytz

# Config
PROJECT_ID = "cityinsightmaps"
LOCATION = "us-central1"
AGENT_1_ID = "projects/1092037303200/locations/us-central1/reasoningEngines/8559187848840871936"
AGENT_2_ID = "projects/1092037303200/locations/us-central1/reasoningEngines/6597659104888487936"
IST = timezone(timedelta(hours=5, minutes=30))

def main(request):
    # Init VertexAI and Firestore
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    db = firestore.Client()

    # ---------------------------
    # 1. Run Agent 1: Get Raw Text
    # ---------------------------
    agent1 = agent_engines.get(AGENT_1_ID)
    session1 = agent1.create_session(user_id="agent1_trigger")
    session_id1 = session1["id"]

    fused_text = ""
    for event in agent1.stream_query(user_id="agent1_trigger", session_id=session_id1, message="summarize me"):
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                fused_text += part["text"].strip() + "\n"

    now_ist = datetime.now(IST)
    timestamp_str = now_ist.isoformat()
    doc_name = f"event_{now_ist.strftime('%Y%m%d_%H%M%S')}"

    # Write to raw_events_data
    db.collection("raw_events_data").document(doc_name).set({
        "timestamp": timestamp_str,
        "raw_description": fused_text.strip()
    })

    # ---------------------------
    # 2. Run Agent 2: Get JSON Events
    # ---------------------------
    combined_input = f"{timestamp_str}\n{fused_text.strip()}"
    agent2 = agent_engines.get(AGENT_2_ID)
    session2 = agent2.create_session(user_id="agent2_trigger")
    session_id2 = session2["id"]

    structured_events = []
    for response in agent2.stream_query(user_id="agent2_trigger", session_id=session_id2, message=combined_input):
        content = response.get("content", {})
        for part in content.get("parts", []):
            if "text" in part:
                try:
                    parsed = json.loads(part["text"])
                    if isinstance(parsed, list):
                        structured_events.extend(parsed)
                except Exception as e:
                    print("❌ JSON parse error from agent 2:", e)

    # ---------------------------
    # 3. Write to events_data and current_events_data
    # ---------------------------
    # Clear current_events_data
    for doc in db.collection("current_events_data").stream():
        doc.reference.delete()

    # Store all events
    for idx, event_data in enumerate(structured_events):
        event_id = f"{doc_name}_{idx+1:03d}"
        db.collection("events_data").document(event_id).set(event_data)
        db.collection("current_events_data").document(event_id).set(event_data)

    return {
        "status": "success",
        "raw_description": fused_text.strip(),
        "structured_count": len(structured_events)
    }, 200
