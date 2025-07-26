from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk import Agent
from google.adk.tools import google_search
from .tools import reddit_search, toi_search

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

mood_agent=Agent(
    name="mood_agent",
    model="gemini-2.5-flash",
    description=(
        'Uses information from  times of india, reddit to guage the mood of different places in Bangalore'
    ),
    instruction="""
    You are an agent to guage the mood of different localities from Bengaluru
    You have access to the following tools : 
    reddit_search, toi_search and google_search
    "Majestic",
    "KR Market",
    "MG Road",
    "Shivajinagar",
    "Richmond Town",
    "Electronic City",
    "Whitefield",
    "Marathahalli",
    "Outer Ring Road",
    "Koramangala",
    "HSR Layout",
    "Indiranagar",
    "Jayanagar",
    "Basavanagudi",
    "Banashankari",
    "Malleshwaram",
    "Yelahanka",
    "Hebbal",
    "Silk Board",
    "Bellandur",
    "Kengeri",
    "Bommanahalli",
    "BTM Layout"
    For each of these localities, you can use the tools multiple times to guage the mood of the user.
    Give out a single string output that contains the description of the mood for each of the locality
    the string output should clearly mention the locality name and  its mood.
    Ignore the localities, for which you cannot access the mood
    """,
    tools=[reddit_search,toi_search]
)

root_agent=mood_agent


