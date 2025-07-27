# eval.py

import vertexai
from vertexai import agent_engines
from vertexai.preview.agent_engines.sessions import Session  # ✅ Required for artifact upload
from google.cloud import firestore
import requests
import json

# Step 1: Initialize Vertex AI and Firestore
vertexai.init(project="cityinsightmaps", location="us-central1")
db = firestore.Client(project="cityinsightmaps")

# Step 2: Fetch Firestore document
doc_ref = db.collection("raw_user_data").document("data1")
doc = doc_ref.get()
if not doc.exists:
    raise Exception("Firestore document not found.")
data = doc.to_dict()
image_url = data.get("imageUrl")
if not image_url:
    raise Exception("No imageUrl found in document.")

print(f"🧾 Pulled Firestore document with image URL:\n{image_url}")

# Step 3: Download image from Firebase Storage
img_response = requests.get(image_url)
if img_response.status_code != 200:
    raise Exception("Failed to download image from Firebase URL.")
image_bytes = img_response.content
print("📥 Image downloaded from Firebase.")

# Step 4: Connect to deployed agent engine
agent_engine = agent_engines.get(
    "projects/1092037303200/locations/us-central1/reasoningEngines/8027763092811153408"
)

# Step 5: Create session ID and wrap as Session object
session_dict = agent_engine.create_session(user_id="test_firestore_user")
session_id = session_dict["id"]
print(f"✅ Agent session started: {session_id}")

# ✅ Fix: Wrap the session ID using Session object (ADK preview)
session = Session(session_id=session_id)

# Step 6: Upload image as artifact
session.upload_artifact(
    name="user_image.png",
    content=image_bytes
)
print("📤 Uploaded image as artifact 'user_image.png'.")

# Step 7: Ask the agent to describe the image
print("💬 Asking agent to describe the image...\n")
collected_responses = []

for event in agent_engine.stream_query(
    user_id="test_firestore_user",
    session_id=session_id,
    message="Please describe the uploaded image from the user."
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

# Step 8: Print response
print("\n🟢 Agent Response:\n")
for item in collected_responses:
    print(f"[{item['source']} - {item['type']}] → {item['value']}\n")
