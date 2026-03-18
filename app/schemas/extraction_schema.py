from pydantic import BaseModel, Field
from typing import Dict, Any

class ExtractionRequest(BaseModel):
    text: str
    schema_def: Dict[str, Any] = Field(..., alias="schema")

class ExtractionResponse(BaseModel):
    extracted_data: Dict[str, Any]
    status: str