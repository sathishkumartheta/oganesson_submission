# main.py

import json
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
import vertexai
from vertexai import agent_engines

PROJECT_ID = "cityinsightmaps"
LOCATION = "us-central1"
MOOD_AGENT_ID = "projects/cityinsightmaps/locations/us-central1/reasoningEngines/1031984021644509184"
MJSON_AGENT_ID = "projects/cityinsightmaps/locations/us-central1/reasoningEngines/1653480770221637632"
IST = timezone(timedelta(hours=5, minutes=30))

def main(request):
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    db = firestore.Client()

    now = datetime.now(IST)
    timestamp_str = now.isoformat()
    doc_name = f"mood_{now.strftime('%Y%m%d_%H%M%S')}"

    # Call mood_map_agent
    mood_agent = agent_engines.get(MOOD_AGENT_ID)
    mood_session = mood_agent.create_session(user_id="mood_map_trigger")
    mood_text = ""

    for event in mood_agent.stream_query(user_id="mood_map_trigger", session_id=mood_session["id"], message="Generate the mood map for Bengaluru"):
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                mood_text += part["text"].strip() + "\n"

    db.collection("raw_mood_data").document(doc_name).set({
        "timestamp": timestamp_str,
        "mood_map": mood_text.strip()
    })

    # Call mjson_agent
    mjson_agent = agent_engines.get(MJSON_AGENT_ID)
    mjson_session = mjson_agent.create_session(user_id="mjson_trigger")
    structured_text = ""
    combined_input = f"{timestamp_str}\n{mood_text.strip()}"

    for event in mjson_agent.stream_query(user_id="mjson_trigger", session_id=mjson_session["id"], message=combined_input):
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                structured_text += part["text"].strip()

    try:
        parsed = json.loads(structured_text)
        mood_list = parsed.get("moods", [])
        assert isinstance(mood_list, list)
    except Exception as e:
        return {"error": f"Failed to parse mood JSON:\n{structured_text}\n\nError: {e}"}, 500

    # Purge and update current_mood_data
    for doc in db.collection("current_mood_data").stream():
        doc.reference.delete()

    for entry in mood_list:
        loc = entry.get("locality")
        if loc:
            db.collection("current_mood_data").document(loc).set(entry)

    return {
        "status": "success",
        "raw_doc": doc_name,
        "inserted": len(mood_list)
    }, 200
