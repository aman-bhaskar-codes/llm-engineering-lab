import logging
from google import genai
from core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.model_name
        self.client = genai.Client(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=15),
        reraise=True
    )
    async def generate_content(self, prompt: str) -> str:
        """Async wrapper for content generation with retry logic."""
        try:
            # Note: SDK might be synchronous, using to_thread if needed 
            # or just calling if it's async-compatible.
            # For this version, we assume the simple call is fine.
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise