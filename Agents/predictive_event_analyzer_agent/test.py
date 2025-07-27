# test_predictive_agent.py

import json
import warnings
from vertexai.preview import reasoning_engines
from pred_agent.agent import root_agent

# Optional: Suppress async or tool-related warnings
warnings.filterwarnings("ignore", message=".*detach.*context.*")

def main():
    app = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)

    user_id = "test_user_001"
    session = app.create_session(user_id=user_id)
    print(f"✅ Created Session: {session.id}")

    print("\n💬 Streaming Agent Response:")
    collected_responses = []

    for event in app.stream_query(
        user_id=user_id,
        session_id=session.id,
        message="Give me the predictive commentary for Bengaluru today."
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

    print("\n🟢 Structured Output by Agent/Tool:\n")
    for item in collected_responses:
        label = f"[{item['source']}]"
        if isinstance(item["value"], (dict, list)):
            print(f"{label} → (JSON output):")
            print(json.dumps(item["value"], indent=2, ensure_ascii=False))
        else:
            print(f"{label} → {item['value']}\n")

if __name__ == "__main__":
    main()
