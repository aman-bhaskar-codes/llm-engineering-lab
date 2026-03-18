import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel(settings.MODEL_NAME)


def generate_text(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)

        if not response or not response.text:
            return ""

        return response.text.strip()

    except Exception as e:
        print("LLM ERROR:", str(e))
        return ""