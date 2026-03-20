"""
Model Router — Factory for LLM client selection.

Supported models:
  - "qwen2.5:3b"  → OllamaClient (local, high quality for size)
  - "phi"          → OllamaClient (local, fastest)
  - "gemini"       → GeminiClient (cloud, highest quality, rate-limited)

Default: qwen2.5:3b (local, no rate limits, fast)
"""
import logging

logger = logging.getLogger(__name__)

# Model → provider mapping
OLLAMA_MODELS = {"qwen2.5:3b", "phi", "phi:latest", "qwen2.5:1.5b"}


def get_llm_client(model_preference: str = "qwen2.5:3b"):
    """
    Returns an LLM client based on preference.
    Defaults to Ollama qwen2.5:3b for reliability (no rate limits).
    Falls back to Gemini only when explicitly requested.
    """
    if model_preference in OLLAMA_MODELS or model_preference.startswith("qwen") or model_preference.startswith("phi"):
        try:
            from llm.ollama_client import OllamaClient
            # Normalize model name
            model_name = model_preference
            if model_preference == "phi":
                model_name = "phi:latest"
            client = OllamaClient(model_name=model_name)
            client.model_name = model_name
            return client
        except Exception as e:
            logger.warning(f"Ollama client init failed for {model_preference}, falling back to Gemini: {e}")

    if model_preference == "gemini" or model_preference.startswith("gemini"):
        try:
            from llm.gemini_client import GeminiClient
            return GeminiClient()
        except Exception as e:
            logger.error(f"Gemini client init failed: {e}")
            raise

    # Default fallback: try Ollama first, then Gemini
    try:
        from llm.ollama_client import OllamaClient
        return OllamaClient()
    except Exception:
        from llm.gemini_client import GeminiClient
        return GeminiClient()
