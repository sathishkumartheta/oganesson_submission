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
    1. Majestic  
    2. MG Road  
    3. Electronic City  
    4. Whitefield  
    5. Koramangala  
    6. Indiranagar  
    7. Jayanagar  
    8. Hebbal  
    9. Silk Board

    For each of these localities, you can use the tools multiple times to guage the mood of the user.
    Give out a single string output that contains the description of the mood for each of the locality
    the string output should clearly mention the locality name and  its mood.
    Ignore the localities, for which you cannot access the mood..
    You need to definitely try both tools for each of the above cities atleast once
    and not more than thrice
    You need to output the mood for all the places. for localities for which you cannot guage the mood
    output that you cannot guage the mood.. but proceed with guaging the mood for other localities
    """,
    tools=[reddit_search,toi_search]
)

root_agent=mood_agent


