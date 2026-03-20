import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.semantic_memory import SemanticMemory


async def upsert_semantic_memory(
    session: AsyncSession,
    user_id: uuid.UUID,
    items: list[tuple[str, dict, list[float] | None]],
    source_extraction_id: uuid.UUID | None,
) -> None:
    """
    Upsert semantic keys for a user with Optional embeddings.
    """
    if not items:
        return

    rows = [
        {
            "user_id": user_id,
            "key": k,
            "value": v,
            "embedding": emb,
            "source_extraction_id": source_extraction_id,
        }
        for k, v, emb in items
    ]

    stmt = pg_insert(SemanticMemory).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[SemanticMemory.user_id, SemanticMemory.key],
        set_={
            "value": stmt.excluded.value,
            "embedding": stmt.excluded.embedding,
            "source_extraction_id": stmt.excluded.source_extraction_id,
        },
    )

    await session.execute(stmt)


async def get_semantic_memory(
    session: AsyncSession, 
    user_id: uuid.UUID, 
    limit: int = 50
) -> list[SemanticMemory]:
    q = (
        select(SemanticMemory)
        .where(SemanticMemory.user_id == user_id)
        .order_by(SemanticMemory.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_semantic_memory_by_vector(
    session: AsyncSession,
    user_id: uuid.UUID,
    vector: list[float],
    limit: int = 5,
) -> list[SemanticMemory]:
    """
    Find most similar semantic memory entries using pgvector distance.
    """
    q = (
        select(SemanticMemory)
        .where(SemanticMemory.user_id == user_id)
        .order_by(SemanticMemory.embedding.l2_distance(vector))
        .limit(limit)
    )
    res = await session.execute(q)
    return list(res.scalars().all())

