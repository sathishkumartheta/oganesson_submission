from google.adk import Agent
from .tools import run_firestore_query, get_firestore_schema

intent_classifer_agent = Agent(
    name="map_query_agent",
    model="gemini-2.5-flash",
    description="Classifies map-related user queries as either navigation or information and extracts relevant locations.",
    instruction="""
        You are a map query intent classifier.

        Your job is to:
        1. Decide whether a query is about `information` (e.g. traffic, air quality, weather) or `navigation` (e.g. directions, route, fastest way).
        2. Extract all location names from the query.

        Return a JSON with:
        - intent: either "information" or "navigation"
        - locations: list of place names mentioned (like Whitefield, Majestic, Silk Board)

        Examples:

        Query: "What's the traffic like in KR Puram?"
        → intent: "information", locations: ["KR Puram"]

        Query: "Take me from Jayanagar to MG Road"
        → intent: "navigation", locations: ["Jayanagar", "MG Road"]

        Query: "Route to Koramangala"
        → intent: "navigation", locations: ["Koramangala"]

        Query: "Is there a power cut in Indiranagar?"
        → intent: "information", locations: ["Indiranagar"]
    """,
)

root_agent=firestore_query_agent 
