import asyncio
import logging
from typing import List, Dict, Any
from core.models.extraction import ExtractionResult
from core.prompts.templates import ADVANCED_EXTRACTION_PROMPT
from llm.gemini_client import GeminiClient
from utils.chunker import Chunker
from utils.json_parser import extract_json, sanitize_json_response

logger = logging.getLogger(__name__)

class AdvancedEngine:
    def __init__(self, client: GeminiClient, chunker: Chunker):
        self.client = client
        self.chunker = chunker

    async def run(self, text: str, schema: dict) -> ExtractionResult:
        logger.info("AdvancedEngine: starting multi-chunk parallel extraction.")
        
        chunks = self.chunker.chunk_text(text)
        tasks = [self._process_chunk(chunk, schema) for chunk in chunks]
        
        chunk_results = await asyncio.gather(*tasks)
        
        # Aggregate results (naive merge, improvements welcome)
        aggregated_data = {}
        total_confidence = 0
        valid = True
        all_issues = []
        
        for res in chunk_results:
            if res:
                aggregated_data.update(res.get("data", {}))
                total_confidence += res.get("confidence", 0)
                if not res.get("valid", True):
                    valid = False
                all_issues.extend(res.get("issues", []))
        
        avg_confidence = total_confidence / len(chunks) if chunks else 0.0
        
        # Final sanitization against whole schema
        final_sanitized = sanitize_json_response(aggregated_data, schema)
        
        return ExtractionResult(
            data=final_sanitized.get("data", {}),
            confidence=avg_confidence,
            mode="advanced",
            valid=valid,
            issues=list(set(all_issues)) # De-duplicate issues
        )

    async def _process_chunk(self, chunk: str, schema: dict) -> Dict[str, Any]:
        prompt = f"{ADVANCED_EXTRACTION_PROMPT}\n\nSchema: {schema}\nText Chunk: {chunk}"
        try:
            response = await self.client.generate_content(prompt)
            raw_json = extract_json(response)
            return sanitize_json_response(raw_json, schema)
        except Exception as e:
            logger.error(f"Chunk processing failed: {e}")
            return {"data": {}, "confidence": 0, "valid": False, "issues": [str(e)]}

    async def run_stream(self, text: str, schema: dict):
        """Streams the extraction progress for multiple chunks."""
        logger.info("AdvancedEngine: starting streaming extraction.")
        chunks = self.chunker.chunk_text(text)
        yield f"<think>\n[Advanced Mode: Processing {len(chunks)} chunks sequentially for streaming]\n"
        
        for idx, chunk in enumerate(chunks, 1):
            yield f"\n--- Processing Chunk {idx}/{len(chunks)} ---\n"
            prompt = f"{ADVANCED_EXTRACTION_PROMPT}\n\nSchema: {schema}\nText Chunk: {chunk}"
            try:
                async for text_chunk in self.client.generate_content_stream(prompt):
                    yield text_chunk
            except Exception as e:
                yield f"\n[Chunk {idx} Error: {e}]\n"
                
        yield "\n</think>\n"
        
