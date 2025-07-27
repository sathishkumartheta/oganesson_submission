import os
import praw
import json
from dotenv import load_dotenv

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_SECRET"),
    user_agent="city_intel_agent"
)

def reddit_search(locality: str) -> str:
    """
    Searches r/bengaluru for recent posts about the given locality.
    Returns a JSON string of relevant posts and comments.
    """
    subreddit = reddit.subreddit("bengaluru")
    results = subreddit.search(locality, sort="new", limit=5)

    mood_data = []
    for post in results:
        try:
            post.comments.replace_more(limit=0)
            comments = [c.body for c in post.comments.list()[:10] if hasattr(c, "body")]
        except Exception:
            comments = []

        mood_data.append({
            "title": post.title,
            "text": post.selftext,
            "comments": comments,
            "score": post.score,
            "url": post.url
        })

    return json.dumps(mood_data, indent=2)

import feedparser
import json

def toi_search(locality: str) -> str:
    """
    Searches TOI Bangalore RSS feed for articles mentioning the given locality.
    Returns a JSON string of matching articles.
    
    Args:
        locality (str): e.g., "BTM Layout", "Majestic", etc.

    Returns:
        str: JSON string of article summaries
    """
    rss_url = "https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms"
    feed = feedparser.parse(rss_url)

    articles = []
    for entry in feed.entries:
        title = entry.title.lower()
        summary = entry.get("summary", "").lower()
        combined = f"{title} {summary}"

        if locality.lower() in combined:
            articles.append({
                "title": entry.title,
                "summary": entry.get("summary", ""),
                "link": entry.link,
                "published": entry.get("published", ""),
                "source": "timesofindia"
            })

    return json.dumps(articles, indent=2)


