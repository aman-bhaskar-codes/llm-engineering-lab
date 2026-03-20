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

    async def generate_content_stream(self, prompt: str):
        """Async generator yielding chunks from Gemini."""
        try:
            # Use the alpha/aio async client for streaming
            if hasattr(self.client, 'aio'):
                response = await self.client.aio.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt
                )
                async for chunk in response:
                    if chunk.text:
                        yield chunk.text
            else:
                import asyncio
                # Fallback to threaded synchronous generator if aio not configured
                def sync_stream():
                    return self.client.models.generate_content_stream(
                        model=self.model_name,
                        contents=prompt
                    )
                response = await asyncio.to_thread(sync_stream)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            raise