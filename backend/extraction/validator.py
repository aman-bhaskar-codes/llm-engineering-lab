from typing import Any, Dict

class Validator:
    @staticmethod
    def validate_extraction(data: Dict[str, Any], schema: Any) -> bool:
        # In a real app, use pydantic to validate
        return True
