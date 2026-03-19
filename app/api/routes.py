from fastapi import APIRouter, HTTPException
from app.schemas.extraction_schema import ExtractionRequest, ExtractionResponse
from app.extraction.engine import run_extraction

router = APIRouter()

DEFAULT_SCHEMA = {
    "name": "string",
    "role": "string",
    "skills": "list[string]",
    "experience_years": "int",
    "education": "string",
    "summary": "string"
}


@router.post("/extract")
async def extract_data(request: ExtractionRequest):

    schema = request.schema_def if request.schema_def else DEFAULT_SCHEMA

    result = await run_extraction(
        request.text,
        schema
    )

    # Return only the extracted data as the main result for a clean interface
    return {
        "status": "success",
        "data": result.get("data"),
        "valid": result.get("valid"),
        "confidence": result.get("confidence")
    }
