from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk import Agent
from .tools import fetch_data,fetch_user


from datetime import datetime
from dotenv import load_dotenv

load_dotenv()





pred_agent=Agent(
    name="pred_agent",
    model="gemini-2.5-flash",
    description=(
        'Analyzes the events in the firestore collections and gives a predictive oneliner'
        'The collections are current_weather_data, current_airquality_data, current_traffic_data and current_events_data'
    ),
    instruction="""
    You are a predictive analyzer agent.
    Use the tool *fetch_data* to fetch the current data from the firestore
    The data will consist of json documents about weather, air quality, traffic 
    and events in the city of bengaluru. Use the tool *fetch_user* to know about 
    your user.. Based on the user data , analyze the json documents and give a 
    predictive one line commentary to the user. Dont just be a reporter.
    Be a predictor. Output a json with two keys.. timestamp:, commentary

    Example Commentary: Dont say traffic jam at Electronic City. 
              Instead say, Avoid going through electronic city.. These are the work around 
              routes in case you need to travel.

    """,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    tools=[fetch_data,fetch_user],

)

root_agent=pred_agent

