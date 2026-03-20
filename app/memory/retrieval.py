import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.semantic_memory import SemanticMemory
from app.db.repositories.semantic_memory import get_semantic_memory, get_semantic_memory_by_vector
from app.utils.embeddings import get_embedding


def _json_dumps(v: Any) -> str:
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)


def build_known_user_context(semantic_entries: list[SemanticMemory], max_chars: int = 2000) -> str:
    """
    Convert semantic_memory rows into a bounded prompt block.
    """
    if not semantic_entries:
        return ""

    lines: list[str] = []
    # Use a set to avoid duplicates if entries were found via both literal and vector search
    seen_keys = set()
    
    for e in semantic_entries:
        if e.key in seen_keys:
            continue
        lines.append(f"{e.key}: {_json_dumps(e.value)}")
        seen_keys.add(e.key)

    block = "\n".join(f"- {l}" for l in lines if l.strip())
    if len(block) > max_chars:
        return block[:max_chars] + "...(truncated)"
    return block


async def fetch_known_user_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
) -> str:
    """Basic recent memory fetch."""
    entries = await get_semantic_memory(db, user_id, limit=limit)
    return build_known_user_context(entries)


async def fetch_semantic_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    query_text: str,
    limit: int = 10,
) -> str:
    """
    Elite retrieval: embed query and find most similar past memories.
    """
    if not query_text or len(query_text) < 10:
        return await fetch_known_user_context(db, user_id, limit=limit)
        
    embedding = await get_embedding(query_text[:1000])
    if not embedding:
        return await fetch_known_user_context(db, user_id, limit=limit)
        
    entries = await get_semantic_memory_by_vector(db, user_id, embedding, limit=limit)
    # Combine with some recent context for safety
    recent = await get_semantic_memory(db, user_id, limit=3)
    
    unique_entries = {e.key: e for e in (entries + recent)}.values()
    return build_known_user_context(list(unique_entries))

