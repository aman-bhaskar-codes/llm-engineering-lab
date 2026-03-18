from typing import Any, Dict
from app.utils.schema_converter import create_dynamic_model

class ExtractionEngine:
    def __init__(self, model_client: Any):
        self.model_client = model_client

    def extract(self, text: str, schema_def: Dict[str, Any]) -> Dict[str, Any]:
        dynamic_model = create_dynamic_model(schema_def)
        return self.model_client.generate_structured(text, dynamic_model)