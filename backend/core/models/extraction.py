from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal

class ExtractionResult(BaseModel):
    data: Dict[str, Any] = Field(..., description="The structured data extracted from the source.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0 to 1.")
    mode: Literal["simple", "advanced", "reasoning"] = Field(..., description="The engine mode used for extraction.")
    valid: bool = Field(True, description="Whether the extraction passed validation.")
    issues: List[str] = Field(default_factory=list, description="List of issues or warnings found during extraction.")

class ExtractionApiResponse(BaseModel):
    conversation_id: Optional[str] = None
    extraction_id: Optional[str] = None
    result: ExtractionResult
    cached: bool = False
