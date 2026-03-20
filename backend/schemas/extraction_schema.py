from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class ExtractionRequest(BaseModel):
    text: str
    schema_def: Optional[Dict[str, Any]] = Field(None, alias="schema")

class ExtractionResponse(BaseModel):
    extracted_data: Dict[str, Any]
    status: str


class ExtractTextRequest(BaseModel):
    text: str
    conversation_id: Optional[UUID] = None
    schema_def: Optional[Dict[str, Any]] = Field(None, alias="schema")


class ExtractRequest(BaseModel):
    text: str
    mode: Optional[str] = "simple"
    model: Optional[str] = "qwen2.5:3b"
    schema_def: Optional[Dict[str, Any]] = Field(None, alias="schema")


class ExtractFileRequest(BaseModel):
    conversation_id: Optional[UUID] = None
    mode: Optional[str] = "simple"


class ExtractionApiResponse(BaseModel):
    conversation_id: Optional[UUID] = None
    extraction_id: Optional[UUID] = None
    result: Dict[str, Any]


# Backwards compatible alias for frontend JSON payload:
# allows clients to send `schema` instead of `schema_def`.
ExtractTextRequest.model_rebuild()
ExtractRequest.model_rebuild()
