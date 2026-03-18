import instructor
from google import genai
from typing import Any, Dict, Type
from pydantic import BaseModel

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        
        # New genai client API
        client = genai.Client(api_key=api_key)
        self.client = instructor.from_genai(
            client=client,
            mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS
        )
        
    def generate_structured(self, prompt: str, schema_model: Type[BaseModel]) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            response_model=schema_model,
            messages=[
                {"role": "user", "content": f"You are a highly precise information extraction system. Return the exact structured data requested based on the input text.\n\nText:\n{prompt}"}
            ]
        )
        return response.model_dump()
