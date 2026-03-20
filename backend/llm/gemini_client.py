from google import genai
from core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

client = genai.Client(api_key=settings.gemini_api_key)

logger = logging.getLogger(__name__)

def log_retry_attempt(retry_state):
    logger.warning(f"Retrying LLM generation. Attempt {retry_state.attempt_number} due to {repr(retry_state.outcome.exception())}")

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1.5, min=2, max=15),
    before_sleep=log_retry_attempt,
    reraise=True
)
def generate_text(prompt: str) -> str:
    response = client.models.generate_content(
        model=settings.model_name,
        contents=prompt
    )
    return response.text