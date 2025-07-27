from google.cloud import firestore
import time

db = firestore.Client()

def write_test_doc():
    doc_data = {
        "Name": "Abc",
        "description": "Pothole",
        "imageUrl": "https://firebasestorage.googleapis.com/v0/b/cityinsightmaps.firebasestorage.app/o/event_media%2Fimages%2Fbengaluru_roads_potholes_1200x768.avif?alt=media&token=821dd5ba-ec18-4dd0-bd8d-c9a4b5aff471",
        "location": "[12.6819372° N, 79.98884129999999° E]",
        "timestamp": int(time.time() * 1000),  # current time in ms
        "type": "UserReported - Abc",
        "userId": "peLf3BWXXiW9W7HkuH2n8bEQNEo2",
        "videoUrl": ""
    }

    doc_ref = db.collection("raw_user_data").document()
    doc_ref.set(doc_data)
    print(f"✅ Test document written to raw_user_data/{doc_ref.id}")

if __name__ == "__main__":
    write_test_doc()
