from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ExtractionRequest(BaseModel):
    text: str
    schema_def: Optional[Dict[str, Any]] = Field(None, alias="schema")

class ExtractionResponse(BaseModel):
    extracted_data: Dict[str, Any]
    status: str