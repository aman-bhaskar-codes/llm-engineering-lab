import asyncio
import os
from app.extraction.engine import ExtractionEngine
from app.llm.gemini_client import GeminiClient
from app.core.config import settings

def main():
    payload = {
        "text": "Alice is a data scientist with 3 years experience in Python and ML",
        "schema": {
            "name": "string",
            "skills": "list[string]",
            "experience_years": "int"
        }
    }
    client = GeminiClient(api_key=settings.gemini_api_key, model_name=settings.model_name)
    engine = ExtractionEngine(model_client=client)
    
    try:
        result = engine.extract(payload["text"], payload["schema"])
        print("EXTRACTION SUCCESS:", result)
    except Exception as e:
        print("EXTRACTION ERROR:", str(e))

if __name__ == "__main__":
    main()
