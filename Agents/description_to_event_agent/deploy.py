# deploy.py

import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import your root agent from the dte_agent package
from dte_agent.agent import root_agent




# --------------------------
# Configuration
# --------------------------
PROJECT_ID = "cityinsightmaps"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://metromind_news_agent"  # Change if using a new bucket

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

    # Create ADK App
    app = reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    # Deploy to Agent Engine
    remote_app = agent_engines.create(
        agent_engine=app,
        requirements=[
            "google-adk",
            "google-generativeai",
            "google-cloud-firestore",
            "google-cloud-aiplatform[adk,agent_engines]",
            "pydantic",
            "cloudpickle"
        ], 
        extra_packages=["./dte_agent"],
        env_vars={
            "GOOGLE_GENAI_USE_VERTEXAI": "TRUE"
        }
    )

    print("✅ Agent deployed successfully!")
    print(f"🔗 Reasoning Engine ID: {remote_app.resource_name}")

if __name__ == "__main__":
    main()
