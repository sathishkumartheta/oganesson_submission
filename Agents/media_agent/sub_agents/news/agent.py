from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk import Agent
from .tools import get_recent_news_articles
def dummy_tool():
    return 1
news_agent=Agent(
    name="news_agent",
    model="gemini-2.5-flash",
    description="Collects recent news articles from timesofindia and summarizes the articles into one summary",
    instruction="""
        You are a news article collector and summarizer agent.
        Use the get_recent_news_articles tools to fetch the news.
        Summarize the fetched news into one single string.
        While summarizing, clearly mention the location names and
        names of the objects like school names, street names etc
    """,
    tools=[get_recent_news_articles],

)