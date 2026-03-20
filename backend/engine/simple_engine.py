import logging
import json
from typing import Dict, Any
from core.models.extraction import ExtractionResult
from core.prompts.templates import SIMPLE_EXTRACTION_PROMPT
from llm.gemini_client import GeminiClient
from utils.json_parser import extract_json, sanitize_json_response

logger = logging.getLogger(__name__)

class SimpleEngine:
    def __init__(self, client: GeminiClient):
        self.client = client

    async def run(self, text: str, schema: dict) -> ExtractionResult:
        logger.info("SimpleEngine: starting single-pass extraction.")
        
        prompt = f"{SIMPLE_EXTRACTION_PROMPT}\n\nSchema: {schema}\nText to extract from: {text}"
        
        try:
            response = await self.client.generate_content(prompt)
            # Use hardened parser to get JSON
            raw_json = extract_json(response)
            
            # Use hardened sanitizer to ensure schema adherence
            # Standard output: {"data": ..., "confidence": ..., "valid": ..., "issues": ...}
            sanitized = sanitize_json_response(raw_json, schema)
            
            return ExtractionResult(
                data=sanitized.get("data", {}),
                confidence=sanitized.get("confidence", 0.9), # Simple mode defaults to high base confidence
                mode="simple",
                valid=sanitized.get("valid", True),
                issues=sanitized.get("issues", [])
            )
        except Exception as e:
            logger.error(f"SimpleEngine failed: {e}")
            return ExtractionResult(
                data={},
                confidence=0.0,
                mode="simple",
                valid=False,
                issues=[f"Engine error: {str(e)}"]
            )
