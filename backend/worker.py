import asyncio
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from loguru import logger

from core.config import settings

redis_settings = RedisSettings.from_dsn(settings.redis_url)

async def _get_redis_pool():
    return await create_pool(redis_settings)

async def process_extraction_job(ctx: dict, job_id: str, text: str, mode: str, user_id: str, model: str = "phi3:mini", schema: dict = None) -> dict:
    import time
    import json
    import uuid
    import redis.asyncio as aioredis
    from core.config import settings
    from llm.model_router import get_llm_client
    from engine.simple_engine import SimpleEngine
    from engine.advanced_engine import AdvancedEngine
    from engine.reasoning_engine import ReasoningEngine
    from utils.chunker import Chunker
    from db.session import AsyncSessionLocal
    from utils.json_parser import extract_json, sanitize_json_response
    from db.repositories.conversations import create_conversation, add_extraction
    from memory.semantic_extractor import extract_semantic_items
    from memory.relationship_repo import get_relationship_repo
    from memory.graph_memory import graph_memory
    from core.prompts.templates import DEFAULT_SCHEMA

    def _get_title(t: str) -> str:
        cleaned = " ".join((t or "").split())
        return cleaned[:40] if cleaned else "New chat"

    logger.info(f"Worker {job_id} started: {mode} mode | User {user_id} | Model {model}")
    if schema is None:
        schema = DEFAULT_SCHEMA

    rc = aioredis.from_url(settings.redis_url, decode_responses=True)
    channel = f"stream:{job_id}"
    chunks_key = f"chunks:{job_id}"
    done_key = f"done:{job_id}"
    result_key = f"result:{job_id}"

    # Clean any stale keys
    await rc.delete(chunks_key, done_key, result_key)

    # ── CRITICAL: Initialize accumulated_text BEFORE inner function ──
    accumulated_text = ""
    start_time = time.time()

    async def safe_stream_to_buffer(generator):
        """Stream tokens to Redis list + notify via pub/sub. Catches all errors."""
        nonlocal accumulated_text
        try:
            async with asyncio.timeout(120):
                async for chunk in generator:
                    # Skip engine error yields — they pollute accumulated text
                    if chunk.startswith("\n[Error") or chunk.startswith("[Error"):
                        continue
                    accumulated_text += chunk
                    await rc.rpush(chunks_key, chunk)
                    await rc.publish(channel, "new_chunk")
        except asyncio.TimeoutError:
            logger.error(f"Worker {job_id} timed out after 120s")
        except Exception as e:
            logger.error(f"Worker {job_id} stream error: {e}")

    def _make_engine(client, engine_mode):
        if engine_mode == "simple":
            return SimpleEngine(client)
        elif engine_mode == "advanced":
            return AdvancedEngine(client, Chunker())
        else:
            return ReasoningEngine(client)

    async def _run_stream(engine, engine_mode):
        if engine_mode == "reasoning":
            await safe_stream_to_buffer(engine.run_stream(text, schema, user_id))
        else:
            await safe_stream_to_buffer(engine.run_stream(text, schema))

    try:
        # ── 1. PRIMARY ATTEMPT ──
        try:
            client = get_llm_client(model)
            engine = _make_engine(client, mode)
            await _run_stream(engine, mode)
        except Exception as e:
            logger.warning(f"Primary model ({model}) failed: {e}")

        # ── 2. FALLBACK if primary produced nothing ──
        if not accumulated_text.strip():
            # Determine fallback model (bidirectional)
            if "gemini" in model.lower():
                fallback_model = "phi3:mini"  # Gemini failed → try Ollama
            else:
                fallback_model = "gemini"  # Ollama failed → try Gemini
            logger.info(f"Worker {job_id}: primary '{model}' empty, falling back to '{fallback_model}'...")
            await rc.delete(chunks_key)
            accumulated_text = ""
            try:
                client = get_llm_client(fallback_model)
                engine = _make_engine(client, mode)
                await _run_stream(engine, mode)
            except Exception as e:
                logger.error(f"Gemini fallback also failed: {e}")

        # ── 3. PARSE & SANITIZE ──
        if not accumulated_text.strip():
            raise RuntimeError("All LLM attempts produced empty output")

        raw_json = extract_json(accumulated_text)
        sanitized = sanitize_json_response(raw_json, schema)

        from core.models.extraction import ExtractionResult
        result = ExtractionResult(
            data=sanitized.get("data", {}),
            confidence=sanitized.get("confidence", 0.9 if mode != "advanced" else 0.8),
            mode=mode,
            valid=sanitized.get("valid", True),
            issues=sanitized.get("issues", [])
        )

        # ── 4. PERSIST TO DB ──
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

        # ── 5. NEO4J (fire-and-forget) ──
        try:
            asyncio.create_task(graph_memory.save_extraction_relations(str(user_id), result.model_dump()))
        except Exception:
            pass

        # ── 6. SIGNAL COMPLETION ──
        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Worker {job_id} completed in {elapsed}s")
        final_payload = {
            "conversation_id": str(conversation.id),
            "extraction_id": str(extraction_obj.id),
            "result": result.model_dump()
        }
        await rc.set(result_key, json.dumps(final_payload), ex=600)
        await rc.set(done_key, "1", ex=600)
        await rc.publish(channel, "done")
        await rc.close()

        return {"status": "success", "job_id": job_id}

    except Exception as e:
        logger.error(f"Worker {job_id} FATAL: {e}")
        import traceback
        traceback.print_exc()
        # Signal error to SSE so frontend knows to stop waiting
        error_payload = json.dumps({"error": str(e)})
        await rc.set(result_key, error_payload, ex=600)
        await rc.set(done_key, "error", ex=600)
        await rc.publish(channel, "done")
        await rc.close()
        raise


class WorkerSettings:
    functions = [process_extraction_job]
    redis_settings = redis_settings
    max_jobs = 20
