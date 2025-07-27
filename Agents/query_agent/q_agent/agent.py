from google.adk import Agent


from pydantic import BaseModel, Field

class MapQueryResult(BaseModel):
    intent: str = Field(description="The intent of the query: information, navigation, or other")
    source: str | None = Field(default=None, description="Source location for navigation")
    destination: str | None = Field(default=None, description="Destination location for navigation")
    locations: list[str] = Field(default=[], description="List of location names (for information queries)")
    message: str | None = Field(default=None, description="Fallback message if intent is 'other'")


qa_agent = Agent(
    name="qa_agent",
    model="gemini-2.5-flash",
    description=(
        'Parses the query and get the intent and the locations'
    ),
    instruction="""
    You are a city map assistant. A user provides a free-text query.

        1. Classify the intent as:
        - "information"
        - "navigation"
        - "other"

        2. Based on the intent, extract:
        - For information: a list of locations
        - For navigation: source and destination
        - For other: fallback message

        Respond in JSON format only.

    """,
    output_schema=MapQueryResult
)

root_agent=qa_agent
