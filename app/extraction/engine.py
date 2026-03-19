from app.utils.chunker import chunk_text
from app.llm.gemini_client import generate_text
from app.extraction.prompt_builder import build_extraction_prompt
from app.extraction.aggregator import aggregate_results


async def run_extraction(text: str, schema: dict):

    if not text.strip():
        return {"error": "Empty input text"}

    chunks = chunk_text(text)

    results = []

    for chunk in chunks:

        prompt = build_extraction_prompt(chunk, schema)
        output = generate_text(prompt)

        if output:
            results.append(output)

    if not results:
        return {"error": "No valid extraction from LLM"}

    final_output = aggregate_results(results)

    return final_output


