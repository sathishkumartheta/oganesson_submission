import functions_framework
import json

@functions_framework.http
def process_user_data(request):
    """
    Processes a Firestore event delivered by Eventarc.
    This function logs the event type and the name of the changed document.
    """
    # Eventarc sends event details in the request headers
    event_type = request.headers.get("ce-type")
    event_subject = request.headers.get("ce-subject")

    print(f"✅ Event Received!")
    print(f"💡 Event Type: {event_type}")
    print(f"📄 Document: {event_subject}")

    # The full event payload is in the request body as JSON
    # This is useful for getting the old/new values of the document
    event_data = request.get_json()
    print("\nFull event data:")
    print(json.dumps(event_data, indent=2))
    
    return "OK", 200