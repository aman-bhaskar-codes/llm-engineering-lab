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
from extraction.engine import run_extraction
from ingestion.loader import load_document
from memory.semantic_extractor import extract_semantic_items
from memory.retrieval import fetch_known_user_context, fetch_semantic_context
from memory.relationship_repo import get_relationship_repo
from extraction.engine_premium import run_premium_extraction_pipeline
from schemas.extraction_schema import (
    ExtractionApiResponse,
    ExtractTextRequest,
    ExtractRequest, # Assuming ExtractRequest is a new schema for the updated endpoint
)
from db.repositories.conversations import (
    add_extraction,
    add_messages,
    create_conversation,
    get_conversation,
    list_conversations,
)
from db.repositories.semantic_memory import upsert_semantic_memory
from db.repositories.semantic_memory import get_semantic_memory

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
async def extract_text(
    payload: ExtractRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    _: None = Depends(check_rate_limit)
):
    stored_user_text = payload.text
    mode = payload.mode or "basic"
    
    # 1. Caching
    cache_key = generate_cache_key(stored_user_text, mode)
    cached_result = await cache_get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for {cache_key}")
        await increment_usage(db, user_id)
        return {"result": cached_result, "conversation_id": None, "extraction_id": None, "cached": True}

    # 2. Augmented Retrieval (Personalization)
    if mode == "premium":
        known_context = await fetch_semantic_context(db, user_id, stored_user_text)
    else:
        known_context = await fetch_known_user_context(db, user_id)

    schema = payload.schema_def or DEFAULT_SCHEMA

    # 3. Trace: Extraction Execution
    logger.info(f"--- EXTRACTION START (Text) ---")
    logger.info(f"Mode: {mode}, User: {user_id}, Schema: {schema[:100] if isinstance(schema, str) else 'Custom'}")
    
    try:
        if mode == "premium":
            logger.info("Running Premium Pipeline...")
            result_dict = await run_premium_extraction_pipeline(
                text=stored_user_text,
                schema=schema,
                known_context=known_context
            )
            result = result_dict.get("result", {})
            assistant_content = result_dict.get("assistant_content", "")
        else:
            logger.info("Running Basic Pipeline...")
            extracted_data = await run_extraction(stored_user_text, schema, known_context=known_context)
            # Standardize output (Step 12/Final Output Format)
            result = {
                "data": extracted_data.get("data", extracted_data) if isinstance(extracted_data, dict) else extracted_data,
                "confidence": extracted_data.get("confidence", 0.8) if isinstance(extracted_data, dict) else 0.8,
                "valid": True,
                "issues": []
            }
            assistant_content = json.dumps(extracted_data)
        
        logger.info(f"Extraction success. Valid: {result.get('valid')}")
    except Exception as e:
        logger.error(f"PIPELINE CRASH: {str(e)}")
        from utils.json_parser import sanitize_json_response
        result = sanitize_json_response({"error": str(e)})
        assistant_content = json.dumps(result)
    
    # 4. Save Conversation
    conversation = await create_conversation(
        db,
        user_id=user_id,
        title=_title_from_text(stored_user_text)
    )
    await db.commit()

    # 5. Background / Parallel: Cache & Persist
    extraction_id = None
    try:
        user_msg = Message(role="user", content=stored_user_text)
        assistant_msg = Message(role="assistant", content=assistant_content)

        await add_messages(db, conversation.id, [user_msg, assistant_msg])
        extraction_obj = await add_extraction(
            db,
            conversation.id,
            input_text=stored_user_text,
            extracted_json=result.get("data", result), 
            confidence=result.get("confidence"),
            mode=mode,
            input_type="text"
        )
        if extraction_obj:
            extraction_id = extraction_obj.id

        if extraction_obj and isinstance(result, dict):
            # Pass the result dict to extractor
            logger.info("Updating semantic memory...")
            semantic_items = await extract_semantic_items(result)
            await upsert_semantic_memory(
                db,
                user_id=user_id,
                items=semantic_items,
                source_extraction_id=extraction_obj.id,
            )
            logger.info(f"Memory updated with {len(semantic_items)} items.")

            repo = get_relationship_repo(db)
            try:
                await repo.upsert_relationships(
                    user_id=user_id,
                    semantic_items=[(k, v) for k, v, _ in semantic_items],
                    source_extraction_id=extraction_obj.id,
                )
            except Exception:
                pass

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.exception("DB persist failed for text extraction")
        extraction_id = None

    # 6. Usage & Caching
    await increment_usage(db, user_id)
    await cache_set(cache_key, result)

    return {
        "result": result,
        "conversation_id": conversation_id,
        "extraction_id": extraction_id,
        "cached": False
    }


@router.post("/extract-file")
async def extract_from_file(
    file: UploadFile = File(...),
    conversation_id: uuid.UUID | None = Form(default=None),
    mode: str = Form(default="basic"),
    user_id: uuid.UUID = Depends(get_current_user_id_from_request),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_rate_limit)
):
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # 1. OCR / Load
    orig_text = await asyncio.to_thread(load_document, file_path)
    text = (orig_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    # 2. Context Retrieval
    if mode == "premium":
        known_context = await fetch_semantic_context(db, user_id, text)
    else:
        known_context = await fetch_known_user_context(db, user_id)

    # 3. Trace: Extraction Execution
    logger.info(f"--- EXTRACTION START (PDF) ---")
    logger.info(f"Mode: {mode}, User: {user_id}, File: {file.filename}")
    
    schema = DEFAULT_SCHEMA
    try:
        if mode == "premium":
            logger.info("Running Premium Pipeline (PDF)...")
            result_dict = await run_premium_extraction_pipeline(
                text=text,
                schema=schema,
                known_context=known_context
            )
            result = result_dict.get("result", {})
            assistant_content = result_dict.get("assistant_content", "")
        else:
            logger.info("Running Basic Pipeline (PDF)...")
            extracted_data = await run_extraction(text, schema, known_context=known_context)
            # Standardize output (Step 12/Final Output Format)
            result = {
                "data": extracted_data.get("data", extracted_data) if isinstance(extracted_data, dict) else extracted_data,
                "confidence": extracted_data.get("confidence", 0.8) if isinstance(extracted_data, dict) else 0.8,
                "valid": True,
                "issues": []
            }
            assistant_content = json.dumps(extracted_data)
        
        logger.info(f"PDF Extraction success. Valid: {result.get('valid')}")
    except Exception as e:
        logger.error(f"PDF PIPELINE CRASH: {str(e)}")
        from utils.json_parser import sanitize_json_response
        result = sanitize_json_response({"error": str(e)})
        assistant_content = json.dumps(result)

    # 4. Save Conversation
    if conversation_id:
        conversation = await get_conversation(db, user_id, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id_final = conversation.id
    else:
        conversation = await create_conversation(db, user_id, (file.filename or "PDF"))
        await db.commit()
        conversation_id_final = conversation.id

    # 5. Background / Parallel: Persist
    extraction_id = None
    try:
        stored_user_text = _truncate(text)
        user_msg = Message(role="user", content=stored_user_text)
        assistant_msg = Message(role="assistant", content=assistant_content)

        await add_messages(db, conversation_id_final, [user_msg, assistant_msg])
        extraction_obj = await add_extraction(
            db,
            conversation_id_final,
            input_text=stored_user_text,
            extracted_json=result.get("data", result),
            confidence=result.get("confidence"),
            mode=mode,
            input_type="pdf"
        )
        if extraction_obj:
            extraction_id = extraction_obj.id

        if extraction_obj and isinstance(result, dict):
            logger.info("Updating semantic memory (PDF)...")
            semantic_items = await extract_semantic_items(result)
            await upsert_semantic_memory(
                db,
                user_id=user_id,
                items=semantic_items,
                source_extraction_id=extraction_obj.id,
            )
            logger.info(f"Memory updated with {len(semantic_items)} items for PDF.")

            repo = get_relationship_repo(db)
            try:
                await repo.upsert_relationships(
                    user_id=user_id,
                    semantic_items=[(k, v) for k, v, _ in semantic_items],
                    source_extraction_id=extraction_obj.id,
                )
            except Exception:
                pass

        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("DB persist failed for file extraction")
        extraction_id = None

    return {
        "result": result,
        "conversation_id": conversation_id_final,
        "extraction_id": extraction_id,
        "cached": False
    }


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
