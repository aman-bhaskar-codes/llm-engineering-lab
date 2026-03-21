"""
Model Router — Factory for LLM client selection.

Supported models:
  - "gemma:2b"     → OllamaClient (local, low level)
  - "phi3:mini"    → OllamaClient (local, medium level)
  - "mistral:latest" → OllamaClient (local, high level reasoning)
  - "gemini-1.5-pro" → GeminiClient (cloud, premium, rate-limited)

Default: phi3:mini (local, no rate limits, fast)
"""
import logging

logger = logging.getLogger(__name__)

# Model → provider mapping
OLLAMA_MODELS = {"gemma:2b", "phi3:mini", "mistral:latest"}


def get_llm_client(model_preference: str = "phi3:mini"):
    """
    Returns an LLM client based on preference.
    Defaults to Ollama phi3:mini for reliability (no rate limits).
    Falls back to Gemini only when explicitly requested.
    """
    if model_preference in OLLAMA_MODELS or model_preference.startswith("gemma") or model_preference.startswith("phi3") or model_preference.startswith("mistral"):
        try:
            from llm.ollama_client import OllamaClient
            # Normalize model name
            model_name = model_preference
            if model_preference == "phi3":
                model_name = "phi3:mini"
            if model_preference == "mistral":
                model_name = "mistral:latest"
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
