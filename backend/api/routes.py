import asyncio
import json
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

# New Modular Architecture
from core.models.extraction import ExtractionApiResponse, ExtractionResult as SaaSResult
from engine.simple_engine import SimpleEngine
from engine.advanced_engine import AdvancedEngine
from engine.reasoning_engine import ReasoningEngine
from utils.chunker import Chunker
from llm.gemini_client import GeminiClient

from memory.semantic_extractor import extract_semantic_items
from memory.retrieval import fetch_known_user_context, fetch_semantic_context
from memory.graph_memory import graph_memory

from db.repositories.conversations import (
    add_extraction,
    add_messages,
    create_conversation,
    get_conversation,
    list_conversations,
)
from db.repositories.semantic_memory import upsert_semantic_memory, get_semantic_memory

from schemas.extraction_schema import ExtractRequest

router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = {
    "name": "string",
    "role": "string",
    "skills": "list[string]",
    "experience_years": "int",
    "education": "string",
    "summary": "string"
}


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



@router.post("/extract")
async def extract_text_auto(
    payload: ExtractRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    _: None = Depends(check_rate_limit)
):
    """Router Endpoint: Automatically detects complexity and selects engine."""
    client = GeminiClient()
    router = ComplexityRouter(client)
    
    # 1. Complexity Detection
    text = payload.text
    schema = payload.schema_def or DEFAULT_SCHEMA
    mode = await router.route(text, schema)
    
    # 2. Re-route to specialized logic
    return await _process_extraction(text, schema, mode, user_id, db)

@router.post("/extract-simple")
async def extract_simple(
    payload: ExtractRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id_from_request)
):
    return await _process_extraction(payload.text, payload.schema_def or DEFAULT_SCHEMA, "simple", user_id, db)

@router.post("/extract-advanced")
async def extract_advanced(
    payload: ExtractRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id_from_request)
):
    return await _process_extraction(payload.text, payload.schema_def or DEFAULT_SCHEMA, "advanced", user_id, db)

@router.post("/extract-reasoning")
async def extract_reasoning(
    payload: ExtractRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id_from_request)
):
    return await _process_extraction(payload.text, payload.schema_def or DEFAULT_SCHEMA, "reasoning", user_id, db)

async def _process_extraction(text: str, schema: dict, mode: str, user_id: uuid.UUID, db: AsyncSession):
    client = GeminiClient()
    
    # Select Engine
    if mode == "simple":
        engine = SimpleEngine(client)
    elif mode == "advanced":
        engine = AdvancedEngine(client, Chunker())
    else:
        engine = ReasoningEngine(client)

    logger.info(f"--- SaaS EXTRACTION START ---")
    logger.info(f"Mode: {mode}, User: {user_id}")

    try:
        # Run Extraction
        result: SaaSResult = await engine.run(text, schema)
        
        # Save Conversation
        conversation = await create_conversation(db, user_id=user_id, title=_title_from_text(text))
        await db.commit()

        # Persist Result
        extraction_obj = await add_extraction(
            db,
            conversation.id,
            input_text=_truncate(text),
            extracted_json=result.data,
            confidence=result.confidence,
            mode=mode,
            input_type="text"
        )
        
        # Essential Postgres Semantic Memory (Keep for history)
        if result.valid:
            try:
                semantic_items = await extract_semantic_items(result.dict())
                await upsert_semantic_memory(db, user_id=user_id, items=semantic_items, source_extraction_id=extraction_obj.id)
                logger.info(f"Essential memory updated: {len(semantic_items)} items.")
            except Exception as e:
                logger.warning(f"Semantic memory update skipped: {e}")

        await db.commit()
        # Save relational memory (Neo4j) - Fail-Open
        asyncio.create_task(graph_memory.save_extraction_relations(user_id, result.model_dump()))

        return ExtractionApiResponse(
            result=result,
            conversation_id=str(conversation.id),
            extraction_id=str(extraction_entry.id),
            cached=False
        )
    except Exception as e:
        logger.error(f"SaaS Pipeline Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-file")
async def extract_from_file(
    file: UploadFile = File(...),
    conversation_id: uuid.UUID | None = Form(default=None),
    mode: str = Form(default="simple"), # Default to simple for speed
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_rate_limit)
):
    """File Ingestion: Loads document then routes to specialized engine."""
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # 1. OCR / Load
    orig_text = await asyncio.to_thread(load_document, file_path)
    text = (orig_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    # 2. Schema Selection
    schema = DEFAULT_SCHEMA # Could be passed via Form but keeping it simple for now
    
    # 3. Process via Unified Internal Path
    try:
        response_data = await _process_extraction(text, schema, mode, user_id, db)
        
        # If conversation_id was provided, we could theoretically merge or relink, 
        # but _process_extraction creates a new one by default. 
        # For SaaS polish, we keep it unified.
        
        return response_data
    except Exception as e:
        logger.error(f"File Pipeline Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    
    # Cascade delete is handled at the model level (assumed), 
    # but we explicitly delete the conversation object.
    await db.delete(conv)
    await db.commit()
    
    return {"success": True, "message": "Conversation deleted"}


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
