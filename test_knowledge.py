from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai import Crew, Agent, Task, LLM
import os
os.environ["GEMINI_API_KEY"] = "fake"
gemini_llm = LLM(
    model="gemini/gemini-2.0-pro-exp-02-05",
    api_key="fake"
)
k = StringKnowledgeSource(content="Test content", metadata={"topic": "test"})
c = Crew(
    agents=[Agent(role="test", goal="test", backstory="test", llm=gemini_llm)], 
    tasks=[Task(description="test", expected_output="test", agent=Agent(role="test", goal="test", backstory="test", llm=gemini_llm))], 
    knowledge={"sources": [k], "collection_name": "test"},
    embedder={
        "provider": "google-generativeai",
        "config": {
            "model": "models/embedding-001",
            "api_key": "fake"
        }
    }
)
print("Crew Created")
