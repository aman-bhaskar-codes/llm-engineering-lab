def build_extraction_prompt(text: str, schema: dict) -> str:

    schema_description = "\n".join(
        [f"{k}: {v}" for k, v in schema.items()]
    )

    return f"""
You are an advanced AI information extraction system.

Your job is to:
1. Understand the context deeply
2. Infer missing but obvious information
3. Normalize informal expressions into structured data
4. Extract high-quality structured insights

Rules:
- Convert vague expressions ("around four years") → precise values (4)
- Extract implied skills from context
- Infer roles if possible (e.g., "building APIs" → backend developer)
- DO NOT hallucinate unknown facts
- Return ONLY valid JSON

Schema:
{schema_description}

Text:
{text}

Output JSON:
"""