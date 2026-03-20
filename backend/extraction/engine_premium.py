import json
import asyncio
from typing import Dict, Any, List
from loguru import logger

from extraction.engine import run_extraction
from extraction.chunking import RecursiveCharacterTextSplitter
from llm.gemini_client import generate_text

semaphore = asyncio.Semaphore(5)

async def run_premium_extraction_pipeline(
    text: str,
    schema: Dict[str, Any],
    known_context: str = ""
) -> Dict[str, Any]:
    """
    Elite multi-pass extraction pipeline:
    1. Reasoning: Analyze text for structure & rules
    2. Parallel Extraction: Chunk-based extraction
    3. Aggregation: Merge results
    4. Verification: Judge pass for quality
    """
    async with semaphore:
        # 1. Reasoning Pass
        reasoning = await _reasoning_pass(text, schema)
        logger.info(f"Reasoning completed: {reasoning[:100]}...")

        # 2. Chunking for large text
        splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=500)
        chunks = splitter.split_text(text)
        
        # 3. Parallel Extraction
        tasks = []
        for chunk in chunks:
            tasks.append(run_extraction(chunk, schema, known_context=f"{known_context}\n\nReasoning Guidelines: {reasoning}"))
        
        results = await asyncio.gather(*tasks)
        
        # 4. Aggregation
        aggregated_data = _aggregate_results(results)
        
        # 5. Verification Pass (Judge)
        verification = await _verification_pass(text[:10000], aggregated_data, schema)
        
        return {
            "result": {
                "data": aggregated_data,
                "confidence": verification.get("confidence", 0.8),
                "valid": verification.get("valid", True),
                "issues": verification.get("issues", []),
                "reasoning": reasoning
            },
            "assistant_content": json.dumps(aggregated_data)
        }

async def _reasoning_pass(text: str, schema: Dict[str, Any]) -> str:
    prompt = f"""
    You are a Strategic Reasoning Engine. 
    Analyze the following text and determine the best strategy to extract information according to the schema.
    
    SCHEMA: {json.dumps(schema)}
    
    TEXT: {text[:5000]}
    
    GOAL:
    - Identify key entities.
    - Define normalization rules.
    - Infer missing fields (e.g. seniority).
    
    Return a concise set of reasoning guidelines for a secondary extraction agent.
    """
    return await asyncio.to_thread(generate_text, prompt)

async def _verification_pass(text: str, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
    You are an AI Quality Judge. 
    Review the proposed extraction against the source text and schema.
    
    SOURCE TEXT (snippet): {text[:3000]}
    SCHEMA: {json.dumps(schema)}
    PROPOSED DATA: {json.dumps(data)}
    
    RETURN JSON ONLY:
    {{
        "valid": true/false,
        "confidence": 0.0-1.0,
        "issues": ["list of issues or empty"],
        "summary": "short summary"
    }}
    """
    raw_res = await asyncio.to_thread(generate_text, prompt)
    from utils.json_parser import extract_json
    extracted = extract_json(raw_res)
    if extracted:
        return extracted
    return {"valid": True, "confidence": 0.7, "issues": ["Verification sub-parse failed"]}

def _aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    final_data = {}
    logger.info(f"Aggregating {len(results)} extraction results")
    for res in results:
        # run_extraction returns {"data": {...}, "confidence": ...}
        data = res.get("data") if isinstance(res, dict) and "data" in res else res
        if not isinstance(data, dict):
            logger.warning(f"Unexpected result format in aggregation: {type(data)}")
            continue
            
        for k, v in data.items():
            if k not in final_data:
                final_data[k] = v
            elif isinstance(v, list) and isinstance(final_data[k], list):
                for item in v:
                    if item not in final_data[k]:
                        final_data[k].append(item)
            elif isinstance(v, dict) and isinstance(final_data[k], dict):
                final_data[k].update(v)
    
    logger.info(f"Aggregation complete. Final keys: {list(final_data.keys())}")
    return final_data
