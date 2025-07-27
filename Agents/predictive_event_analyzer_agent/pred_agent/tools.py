from google.cloud import firestore
from typing import Dict, Any

db = firestore.Client("cityinsightmaps")


def fetch_data() -> Dict[str, Any]:
    """
    Fetches the latest documents from Firestore collections:
    - current_weather_data
    - current_airquality_data
    - current_traffic_data
    - current_events_data

    Returns:
        A dictionary with collection names as keys and a list of document dicts as values.
    """
    collections = [
        "current_weather_data",
        "current_airquality_data",
        "current_traffic_data",
        "current_events_data"
    ]
    
    result = {}
    for col in collections:
        docs = db.collection(col).stream()
        result[col] = [doc.to_dict() for doc in docs]
    
    return result


def fetch_user() -> Dict[str, str]:
    """
    Returns the user name and a free-form description written by the user.

    Example output:
    {
        "name": "Sathish",
        "description": "I live in Indiranagar and usually bike to work in Koramangala. I avoid traffic and like clean air."
    }

    For now, returns a static user profile.
    """
    return {
        "name": "Sathish",
        "description": """I live in Indiranagar and usually bike to work in Koramangala. 
        I avoid traffic and I love music"""
    }
