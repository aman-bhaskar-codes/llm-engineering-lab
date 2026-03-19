import asyncio
from app.utils.chunker import chunk_text
from app.llm.gemini_client import generate_text
from app.extraction.prompt_builder import build_extraction_prompt
from app.extraction.aggregator import aggregate_results

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
You are refining structured data extracted from text.

Your job:
- Ensure valid JSON
- Fix incorrect types
- Remove duplicates
- Improve clarity
- Fill obvious missing fields (only if strongly implied)
- Keep it accurate (NO hallucination)

Schema:
{schema}

Extracted Data:
{data}

Return ONLY valid JSON.
"""


# -----------------------------
# 🔹 Main Extraction Pipeline
# -----------------------------
async def run_extraction(text: str, schema: dict):

    if not text or not text.strip():
        return {"error": "Empty input text"}

    # 1️⃣ Chunking
    chunks = chunk_text(text)

    # 2️⃣ Controlled Parallel Processing
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [
        process_chunk(chunk, schema, semaphore)
        for chunk in chunks
    ]

    results = await asyncio.gather(*tasks)

    # 3️⃣ Filter valid outputs
    valid_results = [r for r in results if r]

    if not valid_results:
        return {"error": "All chunk extractions failed"}

    # 4️⃣ Aggregate results
    merged_output = aggregate_results(valid_results)

    # 5️⃣ Final Reasoning + Refinement Pass
    refined_output = generate_text(
        build_refinement_prompt(merged_output, schema)
    )

    return refined_output