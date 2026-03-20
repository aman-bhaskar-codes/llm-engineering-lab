"""
Ollama Client — Local LLM inference via Ollama API.
Optimized for low latency with connection pooling and tuned parameters.
Same interface as GeminiClient for drop-in interchangeability.
"""
import logging
import httpx
from core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Persistent client for connection reuse (avoids TCP handshake per request)
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    return _http_client


class OllamaClient:
    """Local LLM client via Ollama. Supports qwen2.5:3b and phi."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.ollama_model_name

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True
    )
    async def generate_content(self, prompt: str) -> str:
        """Async call to Ollama's /api/generate endpoint."""
        client = _get_http_client()
        try:
            response = await client.post(
                "/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                        "num_ctx": 4096,
                        "top_p": 0.9,
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.ConnectError:
            logger.error(f"Ollama not reachable at {settings.ollama_base_url}")
            raise
        except Exception as e:
            logger.error(f"Ollama generation failed ({self.model_name}): {e}")
            raise

    async def generate_content_stream(self, prompt: str):
        """Async generator yielding chunks from Ollama's /api/generate endpoint."""
        client = _get_http_client()
        import json
        try:
            async with client.stream(
                "POST",
                "/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                        "num_ctx": 4096,
                        "top_p": 0.9,
                    }
                }
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        try:
                            data = json.loads(chunk)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Ollama streaming failed ({self.model_name}): {e}")
            raise
