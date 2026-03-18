def build_extraction_prompt(text: str, schema: dict) -> str:

    schema_description = "\n".join(
        [f"{k}: {v}" for k, v in schema.items()]
    )

    return f"""
You are an intelligent information extraction system.

Extract HIGH-QUALITY structured data.

Rules:
- Infer missing details if strongly implied
- Normalize values (e.g., "three years" → 3)
- Avoid hallucination
- Return ONLY JSON

Schema:
{schema_description}

Text:
{text}
"""