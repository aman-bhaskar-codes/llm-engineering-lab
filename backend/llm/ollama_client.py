"""
Ollama Client — Local LLM inference via Ollama API.
Optimized for low latency with fresh connections per request.
Same interface as GeminiClient for drop-in interchangeability.
"""
from loguru import logger
import httpx
from core.config import settings


class OllamaClient:
    """Local LLM client via Ollama. Supports qwen2.5:3b and phi."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.ollama_model_name
        self.base_url = settings.ollama_base_url

    def _make_client(self) -> httpx.AsyncClient:
        """Create a fresh httpx client. Avoids stale connection issues in arq workers."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
        )

    async def generate_content(self, prompt: str) -> str:
        """Async call to Ollama's /api/generate endpoint."""
        async with self._make_client() as client:
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
                logger.error(f"Ollama not reachable at {self.base_url}")
                raise
            except Exception as e:
                logger.error(f"Ollama generation failed ({self.model_name}): {e}")
                raise

    async def generate_content_stream(self, prompt: str):
        """Async generator yielding token chunks from Ollama's streaming API."""
        import json as json_mod
        logger.info(f"Ollama streaming: model={self.model_name} url={self.base_url}")
        async with self._make_client() as client:
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
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json_mod.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield token
                        except json_mod.JSONDecodeError:
                            pass
            except Exception as e:
                logger.error(f"Ollama streaming failed ({self.model_name}): {e}")
                raise
