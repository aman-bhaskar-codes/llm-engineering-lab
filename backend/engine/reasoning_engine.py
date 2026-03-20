import logging
import json
from typing import Dict, Any, List
from core.models.extraction import ExtractionResult
from core.prompts.templates import REASONING_EXTRACTION_PROMPT
from llm.gemini_client import GeminiClient
from utils.json_parser import extract_json, sanitize_json_response
from memory.graph_memory import graph_memory

logger = logging.getLogger(__name__)

class ReasoningEngine:
    def __init__(self, client: GeminiClient):
        self.client = client

    async def run(self, text: str, schema: dict, user_id: str = None) -> ExtractionResult:
        logger.info("ReasoningEngine: starting multi-pass deep extraction.")
        
        # 0. Context Retrieval
        graph_context = {}
        if user_id:
            graph_context = await graph_memory.get_user_context(user_id)
            logger.info(f"ReasoningEngine: Loaded graph context for user {user_id}")

        # 1. Initial Pass
        logger.info("ReasoningEngine Pass 1: Initial Extraction")
        initial_res = await self._extraction_pass(text, schema, graph_context)
        
        # 2. Refinement Pass (Deep Reasoning)
        logger.info("ReasoningEngine Pass 2: Refinement & Inferencing")
        refined_res = await self._refinement_pass(text, schema, initial_res, graph_context)
        
        # 3. Verification Pass
        logger.info("ReasoningEngine Pass 3: Verification & Confidence Scoring")
        final_verified = await self._verification_pass(text, schema, refined_res, graph_context)
        
        sanitized = sanitize_json_response(final_verified, schema)
        
        return ExtractionResult(
            data=sanitized.get("data", {}),
            confidence=sanitized.get("confidence", 0.95),
            mode="reasoning",
            valid=sanitized.get("valid", True),
            issues=sanitized.get("issues", [])
        )

    async def _extraction_pass(self, text: str, schema: dict, context: dict) -> Dict[str, Any]:
        prompt = f"""
        {REASONING_EXTRACTION_PROMPT}
        PREVIOUS CONTEXT (Graph Memory): {context}
        Schema: {schema}
        Task: Perform INITIAL extraction.
        Text: {text[:4000]}
        """
        response = await self.client.generate_content(prompt)
        return extract_json(response)

    async def _refinement_pass(self, text: str, schema: dict, previous_result: dict, context: dict) -> Dict[str, Any]:
        prompt = f"""
        {REASONING_EXTRACTION_PROMPT}
        Task: REFINEMENT. Evaluate previous results and infer deeper relationships.
        PREVIOUS CONTEXT (Graph Memory): {context}
        Previous Result: {previous_result}
        Schema: {schema}
        Text: {text[:4000]}
        
        Focus on: Normalizing values, identifying implied skills/roles, and reconciling with previous context.
        """
        response = await self.client.generate_content(prompt)
        return extract_json(response)

    async def _verification_pass(self, text: str, schema: dict, previous_result: dict, context: dict) -> Dict[str, Any]:
        prompt = f"""
        {REASONING_EXTRACTION_PROMPT}
        Task: VERIFICATION. Check the extracted data for consistency and hallucinations.
        PREVIOUS CONTEXT (Graph Memory): {context}
        Data to Verify: {previous_result}
        Schema: {schema}
        Text: {text[:4000]}
        
        RULES:
        1. Flag any hallucinations (data not in text).
        2. Assign a confidence score from 0.0 to 1.0.
        3. Confirm if new data contradicts or updates Graph Memory.
        4. Output JSON with fields: data, confidence, issues, valid.
        """
        response = await self.client.generate_content(prompt)
        return extract_json(response)
