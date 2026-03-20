import json
import re
import logging
from typing import Any, Dict, List, Optional

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

def find_json_block(text: str) -> str | None:
    """Find the most likely JSON block in a string of text."""
    if not text:
        return None
    
    # 1. Look for markdown code blocks
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, text)
    if matches:
        return max(matches, key=len).strip()
    
    # 2. Look for the first major object/array
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
        
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    end = text.rfind(closer) + 1
    
    if end <= start:
        return None
        
    return text[start:end]

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Robustly extract and normalize JSON from LLM output."""
    if not text:
        return None
        
    try:
        json_str = find_json_block(text)
        if not json_str:
            # Fallback regex for extremely messy output
            match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                return None
            
        data = json.loads(json_str)
        return normalize_text(data)
    except Exception as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return None

def sanitize_json_response(data: Any) -> Dict[str, Any]:
    """
    Ensure API response is ALWAYS a valid dictionary with the strict
    SaaS schema required (Step 12/Final Output Format).
    """
    default_response = {
        "data": {},
        "confidence": 0.0,
        "valid": False,
        "issues": ["Sanitized from non-dictionary or error state"]
    }

    if not data:
        return default_response

    if isinstance(data, dict):
        # Merge with default to ensure all fields exist
        # If 'data' is already a key, use that. Otherwise, data is the data.
        return {
            "data": data.get("data", data if "data" not in data else {}),
            "confidence": data.get("confidence", 0.0),
            "valid": data.get("valid", True if "error" not in data else False),
            "issues": data.get("issues", [])
        }
    
    # If it's a list or other types, wrap it in 'data'
    return {
        "data": data,
        "confidence": 0.5,
        "valid": True,
        "issues": []
    }