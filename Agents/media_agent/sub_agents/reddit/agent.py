from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk import Agent
from .tools import get_recent_posts_with_details


def dummy_tool():
    return 1

reddit_agent=Agent(
    name="reddit_agent",
    model="gemini-2.5-flash",
    description="Collects recent posts and comments from reddit and summarizes the posts and comments into one summary",
    instruction="""
        You are a reddit posts collector and summarizer agent.
        Use the get_recent_posts_with_details tool to fetch the posts and comments.
        Summarize the fetched posts and comments into one single string.
        While summarizing, clearly mention the location names and
        names of the objects like school names, street names etc
    """,
    tools=[get_recent_posts_with_details],

    

)