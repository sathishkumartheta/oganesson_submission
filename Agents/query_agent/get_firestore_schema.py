from google.cloud import firestore

def get_firestore_schema(project_id=None, sample_limit=10):
    db = firestore.Client(project=project_id) if project_id else firestore.Client()
    schema = {}

    print("🔍 Scanning collections...\n")
    for collection in db.collections():
        collection_id = collection.id
        field_set = set()
        print(f"📁 Collection: {collection_id}")
        for doc in collection.limit(sample_limit).stream():
            doc_fields = doc.to_dict().keys()
            field_set.update(doc_fields)
        schema[collection_id] = sorted(list(field_set))
        print(f"  🧬 Fields: {sorted(field_set)}\n")

    return schema

if __name__ == "__main__":
    # Set project_id = "your-project-id" if needed
    schema = get_firestore_schema()
