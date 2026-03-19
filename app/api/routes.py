from fastapi import APIRouter
from app.schemas.extraction_schema import ExtractionRequest, ExtractionResponse
from app.extraction.engine import run_extraction
from fastapi import HTTPException

router = APIRouter()

DEFAULT_SCHEMA = {
    "name": "string",
    "skills": "list[string]",
    "experience_years": "int",
    "role": "string",
    "summary": "string"
}


@router.post("/extract")
async def extract_data(request: ExtractionRequest):

    schema = request.schema_def or DEFAULT_SCHEMA

    result = await run_extraction(
        request.text,
        schema
    )

    return {"result": result}
