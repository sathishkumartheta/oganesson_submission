from google.cloud import aiplatform_v1

client = aiplatform_v1.ReasoningEngineServiceClient()

parent = "projects/cityinsightmaps/locations/global"  # ✅ Use global
engines = client.list_reasoning_engines(parent=parent)

for engine in engines:
    print(engine.name)
