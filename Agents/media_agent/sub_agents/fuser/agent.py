from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk import Agent

def dummy_tool():
    return 1

fuser_agent=Agent(
    name="fuser_agent",
    model="gemini-2.5-flash",
    description="Fuses the news articles from reddit and timesofindia",
    instruction="""
        You are a fuser agent. You will receive summary of the events that happened
        in the past few minutes from two different sources. reddit and timesofindia.
        Your job is to fuse the summaries into one single summary of multiple events
    
    """
)