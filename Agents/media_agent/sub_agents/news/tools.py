from google.cloud import firestore
import praw
import feedparser
from datetime import datetime
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()




# ------------------------------
# Tool 1: News Article Fetcher
# ------------------------------
def get_recent_news_articles() -> str:
    """
    Fetches news from a Bengaluru-specific RSS feed and returns a list of articles.
    """
    rss_url = "https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms"
    feed = feedparser.parse(rss_url)

    articles = []
    for entry in feed.entries[:10]:
        articles.append({
            "id": entry.get("id", entry.get("link", "")),
            "title": entry.title,
            "summary": entry.get("summary", ""),
            "link": entry.link,
            "published": entry.get("published", ""),
            "source": "news"
        })
    return str(articles)


