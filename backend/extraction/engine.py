import asyncio
import logging
from utils.chunker import chunk_text
from llm.gemini_client import generate_text
from extraction.prompt_builder import build_extraction_prompt
from extraction.aggregator import aggregate_results
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

# Controls
MAX_CONCURRENT_REQUESTS = 3
MAX_RETRIES = 2


# -----------------------------
# 🔹 Chunk Processing Worker
# -----------------------------
async def process_chunk(
    chunk: str,
    schema: dict,
    known_context: str | None,
    semaphore: asyncio.Semaphore,
):

    async with semaphore:

        for attempt in range(MAX_RETRIES):

            try:
                prompt = build_extraction_prompt(chunk, schema, known_context=known_context)

                output = await asyncio.to_thread(generate_text, prompt)

                if output and output.strip():
                    return output

            except Exception:
                logger.exception("Chunk extraction error (attempt %s)", attempt + 1)

        return None


# -----------------------------
# 🔹 Production-Grade Prompt (Step 3)
# -----------------------------
def build_stable_extraction_prompt(text: str, schema: dict, known_context: str | None = None):
    return f"""
YOU ARE A HIGH-PRECISION EXTRACTION ENGINE.

TASK:
Extract structured data from the text according to the SCHEMA.

STRICT CONSTRAINTS:
1. Return ONLY valid JSON.
2. DO NOT use ```json code blocks or any markdown tags.
3. DO NOT include any conversational text, explanations, or chatter.
4. Ensure all extracted fields exactly match the SCHEMA below.
5. If a value is missing, use null (do not invent information).

EXTERNAL CONTEXT (Use if relevant):
{known_context if known_context else "None"}

SCHEMA:
{schema}

TEXT TO EXTRACT FROM:
{text}
"""

# -----------------------------
# 🔹 Simplified Stable Pipeline (Step 2 & 6)
# -----------------------------
async def run_extraction(text: str, schema: dict, known_context: str | None = None):
    from utils.json_parser import sanitize_json_response

    if not text or not text.strip():
        return sanitize_json_response({"error": "Empty input provided"})

    logger.info("Starting STABILIZED single-pass extraction.")
    
    # Trace Input
    logger.debug(f"Input size: {len(text)}")

    try:
        # Step 2: Single LLM Call
        prompt = build_stable_extraction_prompt(text, schema, known_context)
        raw_output = await asyncio.to_thread(generate_text, prompt)
        
        if not raw_output:
            logger.error("LLM returned empty output.")
            return sanitize_json_response({"error": "LLM returned empty result"})

        # Step 4: Robust JSON Extraction
        extracted_data = extract_json(raw_output)
        
        if not extracted_data:
            logger.warning("Failed to parse JSON from LLM output. Attempting sanitization.")
            # Fallback (Step 4)
            return sanitize_json_response({"raw_failed_output": raw_output[:500]})

        # Step 12/Final Output Format
        return {
            "data": extracted_data,
            "confidence": 0.85, # Default for simple mode
            "valid": True,
            "issues": []
        }

    except Exception as e:
        logger.exception("Core extraction pipeline failed.")
        return sanitize_json_response({"error": str(e)})