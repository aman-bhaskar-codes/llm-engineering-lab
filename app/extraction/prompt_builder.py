def build_extraction_prompt(text: str, schema: dict) -> str:

    schema_description = "\n".join(
        [f"{k}: {v}" for k, v in schema.items()]
    )

    return f"""
You are an advanced AI information extraction system.

You are a precise information extraction system.

Your job is to:
1. Extract data that is EXPLICITLY mentioned in the text.
2. Normalize values into the requested types (e.g., "four years" to 4).
3. Ensure the output strictly follows the provided schema.

Rules:
- DO NOT add information that is not in the text.
- DO NOT add fields that are not in the schema.
- If a field is not found in the text, return null or an empty value for that field.
- Return ONLY valid JSON.

Schema:
{schema_description}

Text:
{text}

Output JSON:
"""