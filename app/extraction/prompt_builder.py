def build_extraction_prompt(text: str, schema: dict) -> str:
    schema_descrtion = "\n".join(
        [f"{key}: {value}" for key, value in schema.items()]
    )

    prompt = f"""
Extract structured data from the following text.

Return valid JSON matching this schema:

{schema_description}

text:
{text}

Return only JSON.
"""

    return prompt
