import asyncio
from app.utils.chunker import chunk_text
from app.llm.gemini_client import generate_text
from app.extraction.prompt_builder import build_extraction_prompt
from app.extraction.aggregator import aggregate_results
from app.utils.json_parser import extract_json

# Controls
MAX_CONCURRENT_REQUESTS = 3
MAX_RETRIES = 2


# -----------------------------
# 🔹 Chunk Processing Worker
# -----------------------------
async def process_chunk(chunk: str, schema: dict, semaphore: asyncio.Semaphore):

    async with semaphore:

        for attempt in range(MAX_RETRIES):

            try:
                prompt = build_extraction_prompt(chunk, schema)

                output = generate_text(prompt)

                if output and output.strip():
                    return output

            except Exception as e:
                print(f"[Chunk Error] Attempt {attempt + 1}: {e}")

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

- Fix types
- Remove duplicates
- Improve clarity
- Add useful inferred fields if obvious

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
- Check if extracted JSON is correct based on input text
- Detect hallucinations
- Detect incorrect values
- Estimate confidence score (0 to 1)

Return ONLY JSON:

{{
  "is_valid": true/false,
  "confidence": float (0-1),
  "issues": [list of problems]
}}

Text:
{text}

Extracted Output:
{output}
"""

# -----------------------------
# 🔹 Main Pipeline
# -----------------------------
async def run_extraction(text: str, schema: dict):

    if not text.strip():
        return {"error": "Empty input"}

    # 1️⃣ Chunking
    chunks = chunk_text(text)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [
        process_chunk(chunk, schema, semaphore)
        for chunk in chunks
    ]

    results = await asyncio.gather(*tasks)

    valid_results = [r for r in results if r]

    if not valid_results:
        return {"error": "Extraction failed"}

    # 2️⃣ Aggregation
    merged = aggregate_results(valid_results)

    # 3️⃣ Refinement (Intelligence Layer)
    refined = generate_text(
        build_refinement_prompt(merged, schema)
    )

    refined_json = extract_json(refined)

    if not refined_json:
        return {
            "error": "Invalid JSON from refinement",
            "raw": refined
        }

    # 4️⃣ Verification (Confidence Layer)
    verification = generate_text(
        build_verification_prompt(text, refined_json)
    )

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