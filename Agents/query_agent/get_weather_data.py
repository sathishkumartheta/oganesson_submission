from google.cloud import firestore

# Initialize Firestore
db = firestore.Client(project="cityinsightmaps")

def query_current_weather_data():
    all_fields = set()
    print("🌦️ Dumping all location entries from current_weather_data...\n")

    docs = db.collection("current_weather_data").stream()
    for doc in docs:
        data = doc.to_dict()
        city = data.get("city", "Unknown")
        locations = data.get("locations", [])

        for loc in locations:
            name = loc.get("name", "Unnamed")
            print(f"📍 {name} (City: {city})")

            for key, value in loc.items():
                if isinstance(value, dict):
                    for subkey in value.keys():
                        all_fields.add(f"{key}.{subkey}")
                else:
                    all_fields.add(key)

            print(json.dumps(loc, indent=2))
            print("-" * 40)

    print("\n🧬 Inferred field paths in location objects:")
    for field in sorted(all_fields):
        print(f" - {field}")

if __name__ == "__main__":
    import json
    query_current_weather_data()
