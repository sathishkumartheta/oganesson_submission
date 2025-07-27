from google.cloud import firestore
import praw
import feedparser
from datetime import datetime
from typing import List, Dict
import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .sub_agents.news import news_agent
from .sub_agents.reddit import  reddit_agent
from .sub_agents.fuser import fuser_agent

from pydantic import BaseModel, Field
from typing import Literal


class NewsEvent(BaseModel):
    location: str = Field(description="Geographical location of the event, such as a city or landmark.")
    type: Literal["political", "cultural", "weather", "civil", "power cut", "traffic"] = Field(
        description="Type of the news event."
    )
    description: str = Field(description="A brief summary or description of the event.")





load_dotenv()





par_agent=ParallelAgent(
    name="par_agent",
    description="just give two lines of english text",
    sub_agents=[news_agent,reddit_agent],
)

seq_agent=SequentialAgent(
    name="seq_agent",
    description=(
        'Collects news articles from reddit and timesofindia'
        'fuses the articles from both sources'
        'provides output in json format'
        'The output keys are location, type, description'
    ),
    sub_agents=[par_agent,fuser_agent],
    
)
root_agent=seq_agent




