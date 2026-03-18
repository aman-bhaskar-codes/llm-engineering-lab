from fastapi import APIRouter
from app.schemas.extraction_schema import ExtractionRequest, ExtractionResponse
from app.extraction.engine import ExtractionEngine
from app.llm.gemini_client import GeminiClient
from app.core.config import settings
from fastapi import HTTPException

router = APIRouter()

# Initialize dependencies
gemini_client = GeminiClient(api_key=settings.gemini_api_key, model_name=settings.model_name)
extraction_engine = ExtractionEngine(model_client=gemini_client)

@router.post("/extract", response_model=ExtractionResponse)
async def extract_data(payload: ExtractionRequest):
    try:
        extracted = extraction_engine.extract(payload.text, payload.schema_def)
        return ExtractionResponse(extracted_data=extracted, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
