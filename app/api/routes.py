from fastapi import APIRouter, UploadFile, File
from app.extraction.engine import run_extraction
from app.ingestion.loader import load_document
from app.schemas.extraction_schema import ExtractionRequest

router = APIRouter()

DEFAULT_SCHEMA = {
    "name": "string",
    "role": "string",
    "skills": "list[string]",
    "experience_years": "int",
    "education": "string",
    "summary": "string"
}


@router.post("/extract-file")
async def extract_from_file(file: UploadFile = File(...)):

    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    text = load_document(file_path)

    result = await run_extraction(text, DEFAULT_SCHEMA)

    return {"result": result}
