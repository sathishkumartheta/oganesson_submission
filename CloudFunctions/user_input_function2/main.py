import functions_framework
import requests
from google.cloud import firestore
from vertexai.generative_models import GenerativeModel, Part
import vertexai
from datetime import datetime
import pytz

# Initialize Vertex AI and Firestore
vertexai.init(project="cityinsightmaps", location="asia-south1")
db = firestore.Client()

def get_latest_document(collection_name="raw_user_data"):
    docs = db.collection(collection_name).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
    return next(docs, None)

def download_image_bytes(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    raise Exception(f"Failed to fetch image. Status: {response.status_code}")

def build_context(data):
    return f"""User Reported Event:
- Name: {data.get('Name')}
- Type: {data.get('type')}
- Location: {data.get('location')}
- Timestamp: {data.get('timestamp')}
- User ID: {data.get('userId')}

Please describe what you see in this image."""

@functions_framework.http
def process_user_image(request):
    try:
        doc = get_latest_document()
        if not doc:
            return ("❌ No documents found in Firestore collection.", 404)

        data = doc.to_dict()
        image_url = data.get("imageUrl")
        if not image_url:
            return ("❌ No imageUrl found in the latest document.", 400)

        image_bytes = download_image_bytes(image_url)
        prompt = build_context(data)

        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            contents=[
                Part.from_data(image_bytes, mime_type="image/png"),
                prompt
            ],
            generation_config={"max_output_tokens": 256}
        )
        description = response.text.strip()

        # Prepare document to write to Firestore
        ist = pytz.timezone("Asia/Kolkata")
        timestamp = datetime.now(ist).isoformat()

        result_doc = {
            "description": description,
            "timestamp": timestamp,
            "imageUrl": image_url,
            "userId": data.get("userId"),
            "location": data.get("location"),
            "type": data.get("type"),
            "Name": data.get("Name")
        }

        db.collection("current_user_data").add(result_doc)

        return f"✅ Gemini description added to Firestore:\n{description}", 200

    except Exception as e:
        return f"❌ Error: {str(e)}", 500
