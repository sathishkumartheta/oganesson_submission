# deploy_mood_map_agent.py

import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import your root agent
from mm_agent.agent import root_agent  # Adjusted import path

# --------------------------
# Configuration
# --------------------------
PROJECT_ID = "cityinsightmaps"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://metromind_news_agent"
AGENT_ENGINE_NAME = "mood_map_agent"

# --------------------------
# Deployment Logic
# --------------------------
def main():
    # Initialize Vertex AI
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    # Build ADK App
    app = reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    # Deploy to Vertex Agent Engine
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name=AGENT_ENGINE_NAME,
        requirements=[
            "google-adk",
            "google-generativeai",
            "google-cloud-firestore",
            "feedparser",
            "praw",
            "google-cloud-aiplatform[adk,agent_engines]",
            "cloudpickle",
            "google-cloud-trace",
            "pydantic"
        ],
        extra_packages=["./mm_agent"],  # if agent.py is in the same dir
        env_vars={
            "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
            "REDDIT_CLIENT_ID": "u4Hll6W6aRh-bBTCVWmHsg",
            "REDDIT_SECRET": "8gwIrLUSj3fv5Eu4p8q_cOrceUB0yA",
            "REDDIT_USER_AGENT": "MetroMind News Agent"

        }
    )

    print("✅ Mood map agent deployed successfully!")
    print(f"🔗 Reasoning Engine ID: {remote_app.resource_name}")
    print(f"🧠 Agent Name: {AGENT_ENGINE_NAME}")

if __name__ == "__main__":
    main()
