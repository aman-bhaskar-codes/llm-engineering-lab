import json
import re
import logging

logger = logging.getLogger(__name__)

def normalize_text(obj):
    """Recursively normalize strings in a dictionary or list."""
    if isinstance(obj, str):
        # Replace common special characters/entities
        obj = obj.replace("\u2013", "-").replace("\u2014", "-")
        # Remove extra white space
        obj = " ".join(obj.split())
        return obj
    elif isinstance(obj, dict):
        return {k: normalize_text(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_text(i) for i in obj]
    return obj

def extract_json(text: str):
    try:
        if not text:
            return None
            
        # Remove markdown ```json ... ``` blocks
        text = re.sub(r"```json|```", "", text).strip()

        # Find first JSON object or array
        start_obj = text.find("{")
        start_arr = text.find("[")
        
        start = -1
        if start_obj != -1 and start_arr != -1:
            start = min(start_obj, start_arr)
        elif start_obj != -1:
            start = start_obj
        elif start_arr != -1:
            start = start_arr
            
        if start == -1:
            return None
            
        # Determine the closing bracket
        opener = text[start]
        closer = "}" if opener == "{" else "]"
        end = text.rfind(closer) + 1

        if end == 0:
            return None

        json_str = text[start:end]
        data = json.loads(json_str)
        
        # Normalize extracted data (clean strings, etc)
        return normalize_text(data)

    except Exception as e:
        logger.warning("JSON parse error: %s", e)
        return None