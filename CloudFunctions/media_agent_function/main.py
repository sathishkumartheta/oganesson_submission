import json
import os
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
import vertexai
from vertexai import agent_engines

# Define IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# Cloud Function entry point
def main(request):
    # Initialize Vertex AI in the agent's region
    vertexai.init(project="cityinsightmaps", location="us-central1")

    # Load Agent Engine
    agent_engine = agent_engines.get(
        "projects/1092037303200/locations/us-central1/reasoningEngines/8559187848840871936"
    )

    # Create a session
    session = agent_engine.create_session(user_id="cloud_function_trigger")
    session_id = session["id"]

    # Query the agent
    fused_text = ""
    for event in agent_engine.stream_query(
        user_id="cloud_function_trigger",
        session_id=session_id,
        message="summarize me"
    ):
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                fused_text += part["text"].strip() + "\n"

    # Prepare Firestore doc name and IST timestamp
    now_ist = datetime.now(IST)
    doc_name = f"event_{now_ist.strftime('%Y%m%d_%H%M%S')}"

    # Store to Firestore
    db = firestore.Client()
    db.collection("raw_events_data").document(doc_name).set({
        "timestamp": now_ist.isoformat(),
        "description": fused_text.strip()
    })

    return {"status": "success", "summary": fused_text.strip()}, 200
