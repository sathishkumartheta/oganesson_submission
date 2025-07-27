import json
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
import vertexai
from vertexai import agent_engines

# Config
PROJECT_ID = "cityinsightmaps"
LOCATION = "us-central1"
MOOD_AGENT_ID = "projects/cityinsightmaps/locations/us-central1/reasoningEngines/1031984021644509184"
MJSON_AGENT_ID = "projects/cityinsightmaps/locations/us-central1/reasoningEngines/1653480770221637632"
IST = timezone(timedelta(hours=5, minutes=30))

def main(request=None):
    # Initialize Vertex AI and Firestore
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    db = firestore.Client()

    now = datetime.now(IST)
    timestamp_str = now.isoformat()
    doc_name = f"mood_{now.strftime('%Y%m%d_%H%M%S')}"

    # --------------------------
    # Step 1: Run mood_map_agent
    # --------------------------
    mood_agent = agent_engines.get(MOOD_AGENT_ID)
    mood_session = mood_agent.create_session(user_id="mood_map_trigger")
    mood_text = ""

    for event in mood_agent.stream_query(user_id="mood_map_trigger", session_id=mood_session["id"], message="Generate the mood map for Bengaluru"):
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                mood_text += part["text"].strip() + "\n"

    # Save raw mood text to Firestore
    db.collection("raw_mood_data").document(doc_name).set({
        "timestamp": timestamp_str,
        "mood_map": mood_text.strip()
    })
    print(f"✅ Saved raw mood_map to raw_mood_data/{doc_name}")

    # --------------------------
    # Step 2: Run mjson_agent on the raw mood string
    # --------------------------
    mjson_agent = agent_engines.get(MJSON_AGENT_ID)
    mjson_session = mjson_agent.create_session(user_id="mjson_trigger")
    structured_text = ""

    combined_input = f"{timestamp_str}\n{mood_text.strip()}"
    for event in mjson_agent.stream_query(user_id="mjson_trigger", session_id=mjson_session["id"], message=combined_input):
        parts = event.get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                structured_text += part["text"].strip()

    # 🔍 Print raw response before parsing
    print("\n🔎 Raw output from mjson_agent:\n")
    print(structured_text)

    try:
        parsed = json.loads(structured_text)
        mood_list = parsed.get("moods", [])
        assert isinstance(mood_list, list)
    except Exception as e:
        raise ValueError(f"\n❌ Failed to parse mood JSON from mjson_agent:\n\n{structured_text}\n\nError: {e}")

    # --------------------------
    # Step 3: Purge current_mood_data and write new data
    # --------------------------
    purge_count = 0
    for doc in db.collection("current_mood_data").stream():
        doc.reference.delete()
        purge_count += 1

    for entry in mood_list:
        loc = entry.get("locality")
        if loc:
            db.collection("current_mood_data").document(loc).set(entry)

    print(f"🗑️ Purged {purge_count} old documents from current_mood_data")
    print(f"✅ Wrote {len(mood_list)} documents to current_mood_data")

    return {
        "status": "success",
        "purged": purge_count,
        "inserted": len(mood_list),
        "raw_doc": doc_name
    }, 200

if __name__ == "__main__":
    main()
