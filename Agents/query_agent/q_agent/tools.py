from typing import List, Dict, Literal
from pydantic import BaseModel
from google.cloud import firestore

db = firestore.Client()

# 🔧 FIRESTORE SCHEMA (FULL)
FIRESTORE_SCHEMA: Dict[str, List[str]] = {
    "air_quality_data": ["aqi", "location", "pollutant", "timestamp"],
    "bengaluru_air_quality": ["city", "locations", "source", "timestamp_utc"],
    "bengaluru_city_summaries": ["city", "raw_data_timestamps_processed", "summary_period_end", "summary_period_start", "summary_text", "summary_type", "timestamp_generated"],
    "bengaluru_traffic_full_matrix": ["api_provider", "city", "routes", "timestamp"],
    "bengaluru_traffic_routes_v2": ["api_provider", "city", "destination_routes", "source_location", "timestamp"],
    "bengaluru_weather_data": ["city", "locations", "source", "timestamp_utc"],
    "commentary": ["text", "timestamp"],
    "cultural_political_events": ["description", "endTime", "imageUrl", "location", "name", "startTime", "timestamp", "type", "userId", "videoUrl"],
    "current_airquality_data": ["city", "locations", "source", "timestamp"],
    "current_events_data": ["description", "event_type", "location", "timestamp"],
    "current_pred_data": ["data", "timestamp"],
    "current_traffic_data": ["api_provider", "city", "routes", "timestamp"],
    "current_user_data": ["Name", "description", "imageUrl", "location", "timestamp", "type", "userId"],
    "current_weather_data": ["city", "locations", "source", "timestamp"],
    "events_data": ["description", "event_type", "location", "timestamp"],
    "power_cut_data": ["area", "estimatedEndTime", "location", "reason", "startTime"],
    "raw_airquality_data": ["aqi", "aqi_category", "city", "components", "lat", "lon", "source", "timestamp"],
    "raw_events_data": ["description", "timestamp"],
    "raw_pred_data": ["data", "timestamp"],
    "raw_traffic_data": ["api_provider", "city", "routes", "timestamp"],
    "raw_user_data": ["Name", "description", "imageUrl", "location", "name", "timestamp", "type", "userId", "videoUrl"],
    "raw_weather_data": ["city", "cloud_coverage", "country", "lat", "lon", "sunrise", "sunset", "temperature", "timestamp", "weather", "wind"],
    "traffic_data": ["city", "timestamp", "traffic"],
    "traffic_data1": ["description", "location", "severity", "timestamp"],
    "users": ["describe", "email", "joined_date", "name"],
    "weather_data": ["city", "cloud_coverage", "country", "lat", "lon", "sunrise", "sunset", "temperature", "timestamp", "weather", "wind"],
    "weather_data1": ["condition", "humidity", "location", "temperature", "timestamp"],
}

# ---------- 🔧 Tool 1: Run Firestore Query ----------

class FirestoreFilter(BaseModel):
    field: str
    op: Literal["==", "!=", "<", "<=", ">", ">=", "in", "array-contains", "array-contains-any"]
    value: str  # make it string so ADK parses it easily

class FirestoreQueryInput(BaseModel):
    collection: str
    filters: List[FirestoreFilter]

class FirestoreQueryOutput(BaseModel):
    results: List[Dict[str, str]]  # all fields stringified for compatibility

def run_firestore_query(params: FirestoreQueryInput | dict) -> FirestoreQueryOutput:
    if isinstance(params, dict):
        params = FirestoreQueryInput(**params)

    query = db.collection(params.collection)
    for f in params.filters:
        query = query.where(f.field, f.op, f.value)
    
    results = []
    for doc in query.stream():
        doc_dict = doc.to_dict()
        results.append({k: str(v) for k, v in doc_dict.items()})
    
    return FirestoreQueryOutput(results=results)


# ---------- 🔧 Tool 2: Get Firestore Schema ----------

class SchemaInput(BaseModel):
    collection: str

class SchemaOutput(BaseModel):
    fields: List[str]

def get_firestore_schema(params: SchemaInput | dict) -> SchemaOutput:
    if isinstance(params, dict):
        params = SchemaInput(**params)

    if params.collection in FIRESTORE_SCHEMA:
        return SchemaOutput(fields=FIRESTORE_SCHEMA[params.collection])

    docs = db.collection(params.collection).limit(10).stream()
    field_set = set()
    for doc in docs:
        field_set.update(doc.to_dict().keys())
    return SchemaOutput(fields=sorted(list(field_set)))


# ---------- 🧰 ADK Tool Registry ----------

TOOLS = [
    {
        "name": "run_firestore_query",
        "description": "Query Firestore using structured filters like field, operator, and value.",
        "input_model": FirestoreQueryInput,
        "output_model": FirestoreQueryOutput,
        "function": run_firestore_query,
    },
    {
        "name": "get_firestore_schema",
        "description": "Get a list of available fields in a Firestore collection.",
        "input_model": SchemaInput,
        "output_model": SchemaOutput,
        "function": get_firestore_schema,
    }
]
