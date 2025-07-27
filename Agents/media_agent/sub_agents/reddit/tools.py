from google.cloud import firestore
import praw
import feedparser
from datetime import datetime
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()



#--------------------------------
# Tool 1: Reddit Post Fetcher
# ------------------------------
def get_recent_posts_with_details() -> str:
    """
    Fetches recent posts from r/bengaluru on Reddit and returns a list of JSON dictionaries.
    """
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_SECRET"),
        user_agent="city_intel_agent"
    )

    posts = []
    for post in reddit.subreddit("bengaluru").new(limit=10):
        posts.append({
            "id": post.id,
            "title": post.title,
            "url": post.url,
            "created_utc": post.created_utc,
            "score": post.score,
            "num_comments": post.num_comments,
            "comments": [c.body for c in post.comments[:100] if hasattr(c, 'body')],
            "source": "reddit"
        })
    return str(posts)