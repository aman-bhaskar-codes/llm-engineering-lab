import asyncio
import json
import time
import uuid
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.deps import get_current_user_id_from_request, get_db
from core.cache import cache_get, cache_set, generate_cache_key
from core.rate_limit import check_rate_limit
from db.repositories.usage import increment_usage
from db.models.conversation import Conversation
from db.models.semantic_memory import SemanticMemory
from db.models.semantic_relationship import SemanticRelationship
from db.models.extraction import Extraction
from db.models.message import Message

# Modular Architecture
from core.models.extraction import ExtractionApiResponse, ExtractionResult
from engine.simple_engine import SimpleEngine
from engine.advanced_engine import AdvancedEngine
from engine.reasoning_engine import ReasoningEngine
from utils.chunker import Chunker
from llm.model_router import get_llm_client

from memory.semantic_extractor import extract_semantic_items
from memory.retrieval import fetch_known_user_context, fetch_semantic_context
from memory.graph_memory import graph_memory

from ingestion.loader import load_document

from db.repositories.conversations import (
    add_extraction,
    add_messages,
    create_conversation,
    get_conversation,
    list_conversations,
)
from db.repositories.semantic_memory import upsert_semantic_memory, get_semantic_memory

from schemas.extraction_schema import ExtractRequest
from core.prompts.templates import DEFAULT_SCHEMA

from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_STORED_INPUT_CHARS = 20_000


def _title_from_text(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "New chat"
    return cleaned[:40]


def _truncate(text: str) -> str:
    if text is None:
        return ""
    if len(text) <= MAX_STORED_INPUT_CHARS:
        return text
    return text[:MAX_STORED_INPUT_CHARS] + "...(truncated)"


# ──────────────────────────────────────────────────────────────
# UNIFIED EXTRACTION ENDPOINT (all modes)
# ──────────────────────────────────────────────────────────────

from fastapi import Request

@router.post("/extract")
async def extract_unified(
    request: Request,
    payload: ExtractRequest,
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    _: None = Depends(check_rate_limit)
):
    """Unified asynchronous extraction endpoint."""
    text = payload.text
    schema = payload.schema_def
    mode = payload.mode or "simple"
    model = payload.model or "phi3:mini"
    
    job_id = f"job:{uuid.uuid4().hex}"
    
    redis_pool = request.app.state.redis_pool
    if not redis_pool:
        raise HTTPException(status_code=500, detail="Worker pool not initialized")
        
    await redis_pool.enqueue_job("process_extraction_job", job_id, text, mode, str(user_id), model, schema)
    
    return {"job_id": job_id, "status": "queued"}

@router.get("/extract/{job_id}/stream")
async def extract_stream(job_id: str):
    """SSE endpoint — flat protocol with heartbeats to keep connection alive."""
    from core.config import settings
    
    async def event_generator():
        rc = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = rc.pubsub()
        await pubsub.subscribe(f"stream:{job_id}")

        chunks_key = f"chunks:{job_id}"
        done_key = f"done:{job_id}"
        result_key = f"result:{job_id}"

        cursor = 0
        max_wait = 300
        elapsed = 0.0
        hb_counter = 0
        try:
            while elapsed < max_wait:
                # 1. Drain buffer
                chunks = await rc.lrange(chunks_key, cursor, -1)
                if chunks:
                    for chunk in chunks:
                        yield {"data": chunk}
                        cursor += 1
                    elapsed = 0  # reset on activity

                # 2. Check done
                done_val = await rc.get(done_key)
                if done_val is not None:
                    final_chunks = await rc.lrange(chunks_key, cursor, -1)
                    for chunk in final_chunks:
                        yield {"data": chunk}
                        cursor += 1

                    final_res = await rc.get(result_key)
                    if done_val == "error":
                        yield {"data": "[ERROR]" + (final_res or '{"error":"Unknown"}') }
                    elif final_res:
                        yield {"data": "[DONE]" + final_res}
                    else:
                        yield {"data": '[ERROR]{"error":"No result"}'}
                    break

                # 3. Send heartbeat every ~2s to keep connection alive
                hb_counter += 1
                if hb_counter % 4 == 0:  # every 4 * 0.5s = 2s
                    yield {"data": "[HB]"}

                # 4. Wait for pub/sub notification or poll
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                # We waited up to 0.5s
                elapsed += 0.5
            else:
                yield {"data": '[ERROR]{"error":"Timed out"}'}
        finally:
            await pubsub.unsubscribe(f"stream:{job_id}")
            await rc.close()

    return EventSourceResponse(event_generator(), ping=5)


# ──────────────────────────────────────────────────────────────
# FILE EXTRACTION ENDPOINT
# ──────────────────────────────────────────────────────────────

@router.post("/extract-file")
async def extract_from_file(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: uuid.UUID | None = Form(default=None),
    mode: str = Form(default="advanced"),
    model: str = Form(default="phi3:mini"),
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_rate_limit)
):
    """File Ingestion: Loads document then routes to engine."""
    import os
    file_path = f"/tmp/extract_{uuid.uuid4().hex}_{file.filename}"
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())

        orig_text = await asyncio.to_thread(load_document, file_path)
        text = (orig_text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        job_id = f"job:{uuid.uuid4().hex}"
        redis_pool = request.app.state.redis_pool
        if not redis_pool:
            raise HTTPException(status_code=500, detail="Worker pool not initialized")
            
        await redis_pool.enqueue_job("process_extraction_job", job_id, text, mode, str(user_id), model, None)
        return {"job_id": job_id, "status": "queued"}
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ──────────────────────────────────────────────────────────────
# CONVERSATION ENDPOINTS
# ──────────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_user_conversations(
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    db: AsyncSession = Depends(get_db),
):
    convs = await list_conversations(db, user_id)
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at,
        }
        for c in convs
    ]


@router.get("/conversation/{conversation_id}")
async def get_user_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation(db, user_id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    msg_res = await db.execute(msg_q)
    messages = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in msg_res.scalars().all()
    ]

    ex_q = (
        select(Extraction)
        .where(Extraction.conversation_id == conversation_id)
        .order_by(Extraction.created_at.desc())
    )
    ex_res = await db.execute(ex_q)
    extractions = [
        {
            "id": e.id,
            "input_text": e.input_text,
            "extracted_json": e.extracted_json,
            "confidence": e.confidence,
            "mode": e.mode,
            "input_type": e.input_type,
            "created_at": e.created_at,
        }
        for e in ex_res.scalars().all()
    ]

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at,
        "messages": messages,
        "extractions": extractions,
    }


@router.delete("/conversation/{conversation_id}")
async def delete_user_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its associated data."""
    conv = await get_conversation(db, user_id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conv)
    await db.commit()
    return {"success": True, "message": "Conversation deleted"}


# ──────────────────────────────────────────────────────────────
# MEMORY ENDPOINTS
# ──────────────────────────────────────────────────────────────

@router.get("/memory")
async def get_user_memory(
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    db: AsyncSession = Depends(get_db),
):
    semantic_entries = await get_semantic_memory(db, user_id, limit=200)
    semantic = [
        {
            "id": e.id,
            "key": e.key,
            "value": e.value,
            "source_extraction_id": e.source_extraction_id,
            "created_at": e.created_at,
        }
        for e in semantic_entries
    ]

    rel_q = (
        select(SemanticRelationship)
        .where(SemanticRelationship.user_id == user_id)
        .order_by(SemanticRelationship.created_at.desc())
        .limit(500)
    )
    rel_res = await db.execute(rel_q)
    relationships = [
        {
            "id": r.id,
            "from_key": r.from_key,
            "from_value": r.from_value,
            "to_key": r.to_key,
            "to_value": r.to_value,
            "relation_type": r.relation_type,
            "source_extraction_id": r.source_extraction_id,
            "created_at": r.created_at,
        }
        for r in rel_res.scalars().all()
    ]

    return {"semantic": semantic, "relationships": relationships}


@router.get("/user/relational-context")
async def get_user_relational_context_route(
    user_id: str = Depends(get_current_user_id_from_request)
):
    """Retrieves relational context (Neo4j) for the current user."""
    context = await graph_memory.get_user_context(str(user_id))
    return {"context": context}
