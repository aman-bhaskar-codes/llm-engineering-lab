from pydantic import BaseModel
from typing import Dict


class ExtractionRequest(BaseModel):
    text: str
    schema: Dict[str, str]