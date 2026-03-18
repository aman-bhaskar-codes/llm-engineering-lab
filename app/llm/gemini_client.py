from google import genai
from app.core.config import settings

client = genai.Client(api_key=settings.gemini_api_key)

def generate_text(prompt: str) -> str:
    response = client.models.generate_content(
        model=settings.model_name,
        contents=prompt
    )
    return response.text