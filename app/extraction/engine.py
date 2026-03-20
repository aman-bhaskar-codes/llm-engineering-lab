import asyncio
import logging
from app.utils.chunker import chunk_text
from app.llm.gemini_client import generate_text
from app.extraction.prompt_builder import build_extraction_prompt
from app.extraction.aggregator import aggregate_results
from app.utils.json_parser import extract_json

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
# 🔹 Refinement Prompt Builder
# -----------------------------
def build_refinement_prompt(data: dict, schema: dict):

    return f"""
You are an expert data structuring AI.

STRICT RULES:
- Return ONLY raw JSON
- DO NOT use ```json or markdown
- DO NOT add explanation
- Ensure valid JSON format

- Remove ANY fields that are not in the provided Schema.
- Fix types to match the Schema (e.g., convert "four" to 4).
- Remove duplicates and improve clarity.
- STAY LOYAL TO THE SOURCE DATA. Do not invent details.

Schema:
{schema}

Data:
{data}
"""

# -----------------------------
# 🔹 Verification Prompt
# -----------------------------
def build_verification_prompt(text: str, output: str):

    return f"""
You are a strict verification system.

Your job:
- Check if extracted JSON is strictly supported by the input text.
- Flag any field as "hallucinated" if it contains information not in the text.
- Compare the extracted data against the raw text for literal accuracy.
- Estimate confidence score (0 to 1).

Return ONLY JSON:

{{
  "is_valid": true/false,
  "confidence": float (0-1),
  "issues": [list of specific problems like "hallucinated field X", "misinterpreted value Y"]
}}

Text:
{text}

Extracted Output:
{output}
"""

# -----------------------------
# 🔹 Main Pipeline
# -----------------------------
async def run_extraction(text: str, schema: dict, known_context: str | None = None):

    if not text.strip():
        return {"error": "Empty input"}

    # 1️⃣ Chunking
    chunks = chunk_text(text)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [process_chunk(chunk, schema, known_context, semaphore) for chunk in chunks]

    results = await asyncio.gather(*tasks)

    valid_results = [r for r in results if r]

    if not valid_results:
        return {"error": "Extraction failed"}

    # 2️⃣ Aggregation
    merged = aggregate_results(valid_results)

    # 3️⃣ Refinement (Intelligence Layer)
    refined_prompt = build_refinement_prompt(merged, schema)
    refined = await asyncio.to_thread(generate_text, refined_prompt)

    refined_json = extract_json(refined)

    if not refined_json:
        return {
            "error": "Invalid JSON from refinement",
            "raw": refined
        }

    # 4️⃣ Verification (Confidence Layer)
    verification_prompt = build_verification_prompt(text, refined_json)
    verification = await asyncio.to_thread(generate_text, verification_prompt)

    verification_json = extract_json(verification)

    if not verification_json:
        verification_json = {
            "is_valid": False,
            "confidence": 0,
            "issues": ["verification parsing failed"]
        }

    # 5️⃣ Final Output
    return {
        "data": refined_json,
        "confidence": verification_json.get("confidence"),
        "valid": verification_json.get("is_valid"),
        "issues": verification_json.get("issues", [])
    }