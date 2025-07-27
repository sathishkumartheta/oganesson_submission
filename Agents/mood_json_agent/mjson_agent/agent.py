from google.adk import Agent
from pydantic import BaseModel, Field
from typing import Literal, List

class BengaluruMood(BaseModel):
    locality: Literal[
        "Majestic",
        "MG Road",
        "Electronic City",
        "Whitefield",
        "Koramangala",
        "Indiranagar",
        "Jayanagar",
        "Hebbal",
        "Silk Board"
    ] = Field(..., description="One of the 9 predefined key localities in Bengaluru.")

    mood: Literal["positive", "neutral", "negative", "angry", "unable to gauge"] = Field(
        ..., description="Overall mood classification for the locality."
    )

    mood_number: int = Field(..., ge=1, le=5, description="Mood score from 1 (lowest) to 5 (highest).")

    reason: str = Field(..., description="One-line summary explaining why this mood was assigned.")

class MoodMapOutput(BaseModel):
    timestamp: str = Field(..., description="Timestamp when the mood map was generated.")
    moods: List[BengaluruMood] = Field(..., description="List of mood records per locality.")


mood_parser_agent = Agent(
    name="mood_parser_agent",
    model="gemini-2.5-flash",
    description=(
        "Processes the latest mood description string for 9 key Bengaluru localities "
        "and converts it into structured JSON format.\n"
        "Each output JSON object contains the following keys:\n"
        "- locality: One of [Majestic, MG Road, Electronic City, Whitefield, Koramangala, Indiranagar, Jayanagar, Hebbal, Silk Board]\n"
        "- mood: One of [positive, neutral, negative, angry, unable to gauge]\n"
        "- mood_number: Corresponding score from 1 (lowest) to 5 (highest)\n"
        "- reason: One-line justification for the mood label"
    ),
    instruction="""
    You will receive a long descriptive string summarizing public sentiment and issues across 9 Bengaluru localities.

    Perform the following steps:
    1. For each locality mentioned (Majestic, MG Road, Electronic City, Whitefield, Koramangala, Indiranagar, Jayanagar, Hebbal, Silk Board), extract the relevant mood description.
    2. Classify the mood as one of the following: "positive", "neutral", "negative", "angry", "unable to gauge".
    3. Assign a mood number based on the mood:
       - positive → 5
       - neutral → 4
       - negative → 3
       - angry → 2
       - unable to gauge → 1
    4. Extract or summarize a one-line reason for the mood based on the text.
    5. Output only a list of JSON objects — one per locality — with the following keys:
       - locality
       - mood
       - mood_number
       - reason

    ⚠️ Output should be a pure list of JSON objects — no extra text, no headers, no markdown. Each object must correspond to one of the 9 specified localities.
    """,
    output_schema=MoodMapOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = mood_parser_agent
