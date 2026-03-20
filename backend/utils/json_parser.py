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
        # Return the largest match or first
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

def extract_json(text: str):
    """Robustly extract and normalize JSON from LLM output."""
    try:
        json_str = find_json_block(text)
        if not json_str:
            return None
            
        data = json.loads(json_str)
        return normalize_text(data)
    except Exception as e:
        logger.warning(f"Failed to parse JSON: {e}")
        # Try a more aggressive regex for simple structures if needed
        return None

def sanitize_json_response(data: Any) -> Dict[str, Any]:
    """Ensure API response is always a valid dictionary with expected structure."""
    if isinstance(data, dict):
        return data
    if data is None:
        return {"error": "Extraction failed", "data": {}}
    return {"data": data}