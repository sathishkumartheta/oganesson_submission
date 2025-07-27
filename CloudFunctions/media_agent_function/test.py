import requests
import json
import uuid
from google.auth.transport.requests import Request
from google.oauth2 import service_account

# === Setup ===
ENGINE_BASE = "https://us-central1-aiplatform.googleapis.com/v1/projects/cityinsightmaps/locations/us-central1/reasoningEngines/968370676907900928"
SERVICE_ACCOUNT_FILE = "sc.json"  # Replace this

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
credentials.refresh(Request())
access_token = credentials.token

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# === 1. Create session ===
session_id = str(uuid.uuid4())
create_session_url = f"{ENGINE_BASE}/sessions"
session_body = {
    "session": {
        "name": f"{ENGINE_BASE}/sessions/{session_id}"
    },
    "sessionId": session_id
}

response = requests.post(create_session_url, headers=headers, json=session_body)
print("🟢 Create session:", response.status_code)
print(response.text)  # Print full raw response in case of non-JSON body
session_name = response.json()["name"] if response.ok else None

# === 2. Stream input (if session was created successfully) ===
if session_name:
    stream_url = f"{session_name}:streamInput"
    input_body = {
        "input": {
            "text": "Get the latest Bengaluru news"
        }
    }

    r2 = requests.post(stream_url, headers=headers, json=input_body)
    print("🟢 Stream response:", r2.status_code)
    print(json.dumps(r2.json(), indent=2) if r2.ok else r2.text)
else:
    print("❌ Failed to create session.")
