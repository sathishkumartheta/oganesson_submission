# deploy_map_agent.py

import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import your root agent
from q_agent.agent import root_agent  # ← update path if different

# --------------------------
# Configuration
# --------------------------
PROJECT_ID = "cityinsightmaps"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://metromind_news_agent"
AGENT_ENGINE_NAME = "qa_agent"

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
            "google-cloud-aiplatform[adk,agent_engines]",
            "pydantic",
            "cloudpickle"
        ],
        extra_packages=["./q_agent"],
        env_vars={
            "GOOGLE_GENAI_USE_VERTEXAI": "TRUE"
        }
    )

    print("✅ Map query agent deployed successfully!")
    print(f"🔗 Reasoning Engine ID: {remote_app.resource_name}")
    print(f"🧠 Agent Name: {AGENT_ENGINE_NAME}")

if __name__ == "__main__":
    main()
