from app.extraction.prompt_builder import build_extraction_prompt
from app.llm.openai_client import generate_text


async def run_extraction(text: str, schema: dict):

    prompt = build_extraction_prompt(text, schema)

    response = await generate_text (prompt)

    response