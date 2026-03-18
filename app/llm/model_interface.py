from typing import Protocol, Any, Dict

class ModelInterface(Protocol):
    def generate_structured(self, prompt: str, schema: Any) -> Dict[str, Any]:
        ...
