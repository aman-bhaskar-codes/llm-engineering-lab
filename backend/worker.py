import asyncio
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from loguru import logger

from core.config import settings

redis_settings = RedisSettings.from_dsn(settings.redis_url)

async def _get_redis_pool():
    return await create_pool(redis_settings)

async def process_extraction_job(ctx: dict, job_id: str, text: str, mode: str, user_id: str, model: str = "qwen2.5:3b", schema: dict = None) -> dict:
    import time
    from core.config import settings
    from llm.model_router import get_llm_client
    from engine.simple_engine import SimpleEngine
    from engine.advanced_engine import AdvancedEngine
    from engine.reasoning_engine import ReasoningEngine
    from utils.chunker import Chunker
    import redis.asyncio as aioredis
    from db.session import async_session_maker
    from utils.json_parser import extract_json, sanitize_json_response
    from db.repositories.conversations import create_conversation, add_extraction
    from extraction.helpers import _title_from_text
    from memory.semantic_memory import extract_semantic_items, upsert_semantic_memory
    from memory.graph_memory import graph_memory

    logger.info(f"Worker {job_id} started: {mode} mode | User {user_id}")
    if schema is None:
        from core.prompts.templates import DEFAULT_SCHEMA
        schema = DEFAULT_SCHEMA
        
    rc = aioredis.from_url(settings.redis_url, decode_responses=True)
    channel = f"stream:{job_id}"
    
    start_time = time.time()
    
    try:
        client = get_llm_client(model)
        if mode == "simple":
            engine = SimpleEngine(client)
        elif mode == "advanced":
            engine = AdvancedEngine(client, Chunker())
        else:
            engine = ReasoningEngine(client)

        accumulated_text = ""
        
        # 1. STREAM TO PUBSUB
        async for chunk in engine.run_stream(text, schema, user_id) if mode == "reasoning" else engine.run_stream(text, schema):
            accumulated_text += chunk
            await rc.publish(channel, chunk)
            
        # 2. PARSE AND SANITIZE THE FINAL OUTPUT
        raw_json = extract_json(accumulated_text)
        sanitized = sanitize_json_response(raw_json, schema)
        
        # Determine confidence
        from core.models.extraction import ExtractionResult
        result = ExtractionResult(
            data=sanitized.get("data", {}),
            confidence=sanitized.get("confidence", 0.9 if mode != "advanced" else 0.8),
            mode=mode,
            valid=sanitized.get("valid", True),
            issues=sanitized.get("issues", [])
        )

        # 3. SAVE TO DATABASES
        import uuid
        uid = uuid.UUID(user_id)
        
        async with async_session_maker() as db:
            conversation = await create_conversation(db, user_id=uid, title=_title_from_text(text))
            
            extraction_obj = await add_extraction(
                db,
                conversation.id,
                input_text=text[:5000],
                extracted_json=result.data,
                confidence=result.confidence,
                mode=mode,
                input_type="text"
            )

            if result.valid:
                try:
                    semantic_items = await extract_semantic_items(result.model_dump())
                    await upsert_semantic_memory(db, user_id=uid, items=semantic_items, source_extraction_id=extraction_obj.id)
                except Exception as mem_err:
                    logger.warning(f"Worker semantic memory skip: {mem_err}")
                    
            await db.commit()
            
        # 4. NEO4J ASYNC
        asyncio.create_task(graph_memory.save_extraction_relations(str(user_id), result.model_dump()))

        # 5. SEND FINAL PAYLOAD TO PUBSUB to terminate stream
        import json
        final_payload = {
            "conversation_id": str(conversation.id),
            "extraction_id": str(extraction_obj.id),
            "result": result.model_dump()
        }
        await rc.publish(channel, f"\n[DONE_JSON]{json.dumps(final_payload)}")
        await rc.close()
        
        return {"status": "success", "job_id": job_id}

    except Exception as e:
        logger.error(f"Worker {job_id} failed: {e}")
        import json
        await rc.publish(channel, f"\n[ERROR]{json.dumps({'error': str(e)})}")
        await rc.close()
        raise

class WorkerSettings:
    functions = [process_extraction_job]
    redis_settings = redis_settings
    max_jobs = 20
