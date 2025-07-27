# 🧠 MetroMind: An Agentic AI Application

> A real-time, intelligent city summarizer built for the Google Agentic AI Day Hackathon 2025.

## 🚀 Project Overview

Bengaluru produces vast, scattered, and rapidly outdated data—from traffic and civic issues to cultural events. Our agentic application aims to synthesize this noisy, multimodal data into clean, actionable insights and predictive summaries. This empowers citizens, city planners, and stakeholders with a **live, intelligent pulse of the city**.
Youtube video link: https://www.youtube.com/shorts/grbrJJuN7SU

## 🎯 Problem Statement

> “Find the signal in the noise.”

Our goal is to create an **Agentic AI application** that:
- Fuses real-time data from disparate sources (social media, weather, air quality, traffic, user media).
- Synthesizes updates into meaningful, structured summaries.
- Enables geotagged image/video reporting with Gemini-based understanding.
- Adds a predictive layer and visualizes insights via a dynamic map dashboard.

## 📐 Evaluation Criteria

| Criteria | Description |
|----------|-------------|
| **Agentic Thinking** | System designs demonstrate autonomous, tool-using, reasoning-based agents. |
| **Originality & Impact** | Creative, practical, and scalable real-world solutions. |
| **Technical Execution** | Effective integration of Google tools like Gemini, Vertex AI, Firebase, Pub/Sub, and more. |
| **Multimodal Capability** | Agents understand and act on diverse data types (text, images, geospatial info). |
| **Responsibility** | Ethical design, safety, and fairness considered in agent reasoning and outputs. |
| **User Experience** | Intuitive, informative, and helpful UI/UX experience for diverse users. |

## 🧩 Architecture

- **Frontend**: Map-based dashboard with real-time visualizations.
- **Backend**: Cloud Functions + Firestore + Pub/Sub.
- **AI Agents**: Gemini-powered tools using the Agent Engine (Vertex AI).
- **Media Agent**: Processes geotagged image/video uploads and generates structured event descriptions.
- **Summarizer Agent**: Synthesizes noisy inputs into clean summaries.
- **Predictive Agent**: Forecasts future civic events and city-wide disruptions.

## 🌐 Technologies Used

- [x] Vertex AI Agent Engine (ADK)
- [x] Gemini 1.5 Pro
- [x] Google Cloud Functions
- [x] Firestore + Firebase Storage
- [x] Pub/Sub
- [x] Gradio (for tool prototyping)
- [x] Python (ADK agent orchestration)

## 📸 Sample Use Case

1. User uploads a photo of a pothole in Whitefield.
2. Image agent classifies it: `event_type: "infrastructure issue"`, location auto-geotagged.
3. Summarizer aggregates reports in that region: "Multiple users reported poor road conditions in Whitefield."
4. Predictive agent suggests increased congestion over next 24 hours.

## ⚖️ Responsible AI Practices

- All summaries are verified for hallucination and bias.
- Personal identifiers from user uploads are anonymized.
- Predictive outputs include confidence levels and disclaimers.

## 📁 Folder Structure

