from fastapi import APIRouter
from app.schemas.extraction_schema import ExtractionRequest
from app.extraction.engine import run_extraction

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Structured Extraction Engine Running"}

@router.post("/extract")
async def extract_data(request: ExtractionRequest):

    result = await run_extraction(
        request.text,
        request.schema
    )

    return {"result": result}



