# test_mood_agent.py

import json
import warnings
from vertexai.preview import reasoning_engines
from mm_agent import root_agent  # from your uploaded agent (9).py

warnings.filterwarnings("ignore", message=".*detach.*context.*")

def main():
    app = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)

    user_id = "test_mood_user"
    session = app.create_session(user_id=user_id)
    print(f"✅ Created Session: {session.id}")

    print("\n💬 Streaming Mood Map Response:")
    collected_responses = []

    for event in app.stream_query(
        user_id=user_id,
        session_id=session.id,
        message="Generate the mood map for Bengaluru."
    ):
        source = event.get("agent") or event.get("tool") or "unknown"
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
                    value = json.loads(result.replace("'", '"')) if isinstance(result, str) else result
                except Exception:
                    value = result
                collected_responses.append({
                    "source": source,
                    "type": "function_response",
                    "value": value
                })

    print("\n🟢 Mood Summary Output:\n")
    for item in collected_responses:
        label = f"[{item['source']}]"
        if isinstance(item["value"], (dict, list)):
            print(f"{label} → (JSON):\n{json.dumps(item['value'], indent=2, ensure_ascii=False)}\n")
        else:
            print(f"{label} → {item['value']}\n")

if __name__ == "__main__":
    main()
