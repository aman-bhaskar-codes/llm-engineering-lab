from pydantic import create_model, BaseModel
from typing import List, Type, Any

TYPE_MAPPING = {
    "string": str,
    "str": str,
    "int": int,
    "integer": int,
    "float": float,
    "boolean": bool,
    "bool": bool,
    "list[string]": List[str],
    "list[int]": List[int]
}

def create_dynamic_model(schema_def: dict[str, Any], model_name: str = "DynamicExtractionModel") -> Type[BaseModel]:
    fields = {}
    for key, value_type in schema_def.items():
        if isinstance(value_type, str):
            python_type = TYPE_MAPPING.get(value_type.lower().replace(" ", ""), str)
            fields[key] = (python_type, ...)
        else:
            fields[key] = (Any, ...)
            
    return create_model(model_name, **fields)
