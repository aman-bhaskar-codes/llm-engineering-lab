import asyncio
from app.utils.chunker import chunk_text
from app.llm.gemini_client import generate_text
from app.extraction.prompt_builder import build_extraction_prompt
from app.extraction.aggregator import aggregate_results

MAX_CONCURRENT_REQUESTS = 3   # control parallel calls
MAX_RETRIES = 2


async def process_chunk(chunk, schema, semaphore):

    async with semaphore:
        for attempt in range(MAX_RETRIES):

            try:
                prompt = build_extraction_prompt(chunk, schema)

                output = generate_text(prompt)

                if output:
                    return output

            except Exception as e:
                print(f"Chunk error: {e}")

        return None


async def run_extraction(text: str, schema: dict):

    if not text.strip():
        return {"error": "Empty input"}

    chunks = chunk_text(text)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [
        process_chunk(chunk, schema, semaphore)
        for chunk in chunks
    ]

    results = await asyncio.gather(*tasks)

    # remove failed ones
    valid_results = [r for r in results if r]

    if not valid_results:
        return {"error": "All chunk extractions failed"}

    final_output = aggregate_results(valid_results)

    return final_output


