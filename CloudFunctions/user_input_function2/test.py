import requests
from google.cloud import firestore
from vertexai.generative_models import GenerativeModel, Part
import vertexai

# Initialize Vertex AI and Firestore
vertexai.init(project="cityinsightmaps", location="asia-south1")
db = firestore.Client()

def get_latest_document(collection_name="raw_user_data"):
    """Fetches the most recently added document in the given Firestore collection."""
    docs = db.collection(collection_name).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
    return next(docs, None)

def download_image_bytes(url):
    """Downloads image data from Firebase Storage public URL."""
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to fetch image. Status: {response.status_code}")

def build_context(doc):
    """Constructs a prompt from document fields."""
    data = doc.to_dict()
    return f"""User Reported Event:
- Name: {data.get('Name')}
- Type: {data.get('type')}
- Location: {data.get('location')}
- Timestamp: {data.get('timestamp')}
- User ID: {data.get('userId')}

Please describe what you see in this image."""

def main():
    print("📥 Fetching latest user report...")
    doc = get_latest_document()
    if not doc:
        print("❌ No documents found in collection.")
        return

    data = doc.to_dict()
    image_url = data.get("imageUrl")
    if not image_url:
        print("❌ No imageUrl found in document.")
        return

    print(f"🖼️ Downloading image from: {image_url}")
    image_bytes = download_image_bytes(image_url)

    prompt = build_context(doc)

    print("🧠 Calling Gemini Vision model...")
    model = GenerativeModel("gemini-1.5-flash")  # You can also use "gemini-1.5-pro" or "gemini-2.5-flash"

    response = model.generate_content(
        contents=[
            Part.from_data(image_bytes, mime_type="image/png"),
            prompt
        ],
        generation_config={"max_output_tokens": 256}
    )

    print("\n📝 Gemini Description:")
    print(response.text.strip())

if __name__ == "__main__":
    main()
