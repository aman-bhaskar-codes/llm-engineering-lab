import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel(settings.MODEL_NAME)


async def generate_text(prompt: str):
    response = model.generate_content(prompt)
    return response.text