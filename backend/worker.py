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
    from db.session import AsyncSessionLocal
    from utils.json_parser import extract_json, sanitize_json_response
    from db.repositories.conversations import create_conversation, add_extraction
    from memory.semantic_extractor import extract_semantic_items
    from memory.relationship_repo import get_relationship_repo
    from memory.graph_memory import graph_memory

    # Local helper since we don't have a shared one yet
    def _get_title(t: str) -> str:
        cleaned = " ".join((t or "").split())
        if not cleaned:
            return "New chat"
        return cleaned[:40]

    logger.info(f"Worker {job_id} started: {mode} mode | User {user_id}")
    if schema is None:
        from core.prompts.templates import DEFAULT_SCHEMA
        schema = DEFAULT_SCHEMA
        
    rc = aioredis.from_url(settings.redis_url, decode_responses=True)
    channel = f"stream:{job_id}"
    chunks_key = f"chunks:{job_id}"
    done_key = f"done:{job_id}"
    
    # 1. Initialize buffer
    await rc.delete(chunks_key, done_key)
    
    start_time = time.time()
    
    try:
        async def safe_stream_to_buffer(generator):
            nonlocal accumulated_text
            try:
                # Enforce a 90s timeout on the entire stream generation
                async with asyncio.timeout(120):
                    async for chunk in generator:
                        accumulated_text += chunk
                        await rc.rpush(chunks_key, chunk)
                        await rc.publish(channel, "new_chunk")
            except asyncio.TimeoutError:
                err_msg = "\n[ERROR] Request timed out after 120s"
                await rc.rpush(chunks_key, err_msg)
                await rc.publish(channel, "new_chunk")
                logger.error(f"Worker {job_id} timed out")
            except Exception as e:
                err_msg = f"\n[ERROR] Stream interrupted: {str(e)}"
                await rc.rpush(chunks_key, err_msg)
                await rc.publish(channel, "new_chunk")
                logger.error(f"Worker {job_id} stream error: {e}")

        # 2. ATTEMPT EXTRACTION WITH FALLBACK
        try:
            client = get_llm_client(model)
            if mode == "simple":
                engine = SimpleEngine(client)
            elif mode == "advanced":
                engine = AdvancedEngine(client, Chunker())
            else:
                engine = ReasoningEngine(client)

            if mode == "reasoning":
                await safe_stream_to_buffer(engine.run_stream(text, schema, user_id))
            else:
                await safe_stream_to_buffer(engine.run_stream(text, schema))
            
            # Fallback check: if accumulated_text is empty or contains error, try Gemini
            if not accumulated_text or "[ERROR]" in accumulated_text:
                if model != "gemini":
                    logger.info(f"Worker {job_id} falling back to Gemini...")
                    # Clear buffer for fresh attempt
                    await rc.delete(chunks_key)
                    accumulated_text = ""
                    client = get_llm_client("gemini")
                    # Re-init engine with fallback client
                    if mode == "simple": engine = SimpleEngine(client)
                    elif mode == "advanced": engine = AdvancedEngine(client, Chunker())
                    else: engine = ReasoningEngine(client)

                    if mode == "reasoning":
                        await safe_stream_to_buffer(engine.run_stream(text, schema, user_id))
                    else:
                        await safe_stream_to_buffer(engine.run_stream(text, schema))
        except Exception as e:
             logger.error(f"Initial LLM attempt failed: {e}")
             if model != "gemini":
                 # Fallback logic repeated here for total failure to even start stream
                 client = get_llm_client("gemini")
                 engine = SimpleEngine(client) # simpliest for fallback
                 await safe_stream_to_buffer(engine.run_stream(text, schema))
             else:
                 raise
            
        # 3. PARSE AND SANITIZE THE FINAL OUTPUT
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
        
        async with AsyncSessionLocal() as db:
            conversation = await create_conversation(db, user_id=uid, title=_get_title(text))
            
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
                    repo = get_relationship_repo(db)
                    await repo.upsert_relationships(
                        user_id=uid,
                        semantic_items=[(k, v) for k, v, emb in semantic_items],
                        source_extraction_id=extraction_obj.id
                    )
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
        # Store result and mark as done
        await rc.set(f"result:{job_id}", json.dumps(final_payload), ex=600)
        await rc.set(done_key, "1", ex=600)
        
        await rc.publish(channel, f"\n[DONE_JSON]{json.dumps(final_payload)}")
        await rc.close()
        
        return {"status": "success", "job_id": job_id}

    except Exception as e:
        logger.error(f"Worker {job_id} failed: {e}")
        import json
        await rc.set(done_key, "1", ex=600)
        await rc.publish(channel, f"\n[ERROR]{json.dumps({'error': str(e)})}")
        await rc.close()
        raise

class WorkerSettings:
    functions = [process_extraction_job]
    redis_settings = redis_settings
    max_jobs = 20
