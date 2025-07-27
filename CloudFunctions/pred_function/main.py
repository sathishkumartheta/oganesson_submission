import vertexai
from vertexai import agent_engines
from google.cloud import firestore
from datetime import datetime, timedelta, timezone
import pytz
import json

# Config
PROJECT_ID = "cityinsightmaps"
LOCATION = "us-central1"
AGENT_ID = "projects/1092037303200/locations/us-central1/reasoningEngines/1607881823994511360"
IST = timezone(timedelta(hours=5, minutes=30))

def main(request):
    try:
        # Init VertexAI and Firestore
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        db = firestore.Client()

        # Timestamp
        now_ist = datetime.now(IST)
        timestamp_str = now_ist.isoformat()
        doc_name = f"event_{now_ist.strftime('%Y%m%d_%H%M%S')}"

        # Create session and query agent
        agent = agent_engines.get(AGENT_ID)
        session = agent.create_session(user_id="scheduled_runner")
        session_id = session["id"]

        collected_responses = []

        for event in agent.stream_query(
            user_id="scheduled_runner",
            session_id=session_id,
            message="Give me the predictive commentary for Bengaluru today."
        ):
            source = event.get("agent") or event.get("tool") or event.get("name", "root_agent")
            parts = event.get("content", {}).get("parts", [])

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

        # Extract final JSON text output (last "text" entry with json block)
        final_output = None
        for item in reversed(collected_responses):
            if item["type"] == "text":
                text = item["value"].strip()
                if text.startswith("```json"):
                    text = text[7:-3].strip()  # remove ```json and ```
                try:
                    final_output = json.loads(text)
                except Exception as e:
                    print("❌ Error parsing final model output:", e)
                break

        if final_output is None:
            raise ValueError("No valid final output found from agent.")

        # Save to raw_pred_data
        db.collection("raw_pred_data").document(doc_name).set({
            "timestamp": timestamp_str,
            "data": final_output
        })

        # Clear and update current_pred_data
        for doc in db.collection("current_pred_data").stream():
            doc.reference.delete()

        db.collection("current_pred_data").document("latest").set({
            "timestamp": timestamp_str,
            "data": final_output
        })

        return {"status": "success", "timestamp": timestamp_str}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
