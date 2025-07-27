from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk import Agent

from pydantic import BaseModel, Field, RootModel
from typing import Literal, List

class BengaluruEvent(BaseModel):
    location: str = Field(..., description="Specific location of the event in Bengaluru.")
    event_type: Literal["others", "political", "cultural", "powercut", "traffic", "weather", "criminal", "civil"] = Field(
        ..., description="Type of the event. Must be one of: others, political, cultural, powercut, traffic, weather, criminal, civil."
    )
    timestamp: str = Field(..., description="Timestamp of the event as extracted from the input string.")
    description: str = Field(..., description="A one-line description of the event.")

# ✅ Use RootModel for lists in Pydantic v2
class BengaluruEventList(RootModel[List[BengaluruEvent]]):
    pass



seq_agent=Agent(
    name="seq_agent",
    model='gemini-2.5-flash',
    description=(
        'Processes and converts the string of description of events ansd timestamp in bengaluru into a json'
        'The output json should have the following keys'
        'location : specific location of the event in bengaluru'
        'event_type : One of [others,political,cultural,powercut,traffic,weather,criminal,civil]'
        'timestamp : the timestamp stripped from the input string'
        'description: one line description of the event'
    ),
    instruction="""
    Do the following things in order:
    * strip the preceeding datetime from the string *
    * parse the remaining string which contains the description of the events in bengaluru*
    * look for events in the description that can be directly associated with a location in bengaluru *
    * map such events as location: and description *
    * classify each of the events as one of the following  [others,political,cultural,powercut,traffic,weather,criminal,civil] *
    * strictly output only a list of json objects one for each event*
    * each json contains the following keys *
    * location : specific location of the event in bengaluru 
      event_type : One of [others,political,cultural,powercut,traffic,weather,criminal,civil]
      timestamp : the timestamp stripped from the input string
      description: one line description of the event*
    """,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_schema=BengaluruEventList,
)

root_agent=seq_agent
