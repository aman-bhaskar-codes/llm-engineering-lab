import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.conversation import Conversation
from db.models.message import Message
from db.models.extraction import Extraction


async def create_conversation(
    session: AsyncSession,
    user_id: uuid.UUID,
    title: str,
) -> Conversation:
    conv = Conversation(user_id=user_id, title=title, created_at=datetime.utcnow())
    session.add(conv)
    await session.flush()
    return conv


async def list_conversations(session: AsyncSession, user_id: uuid.UUID) -> list[Conversation]:
    q = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at.desc())
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_conversation(
    session: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation | None:
    q = (
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.id == conversation_id)
    )
    res = await session.execute(q)
    return res.scalars().first()


async def add_messages(session: AsyncSession, conversation_id: uuid.UUID, messages: list[Message]) -> None:
    # Caller should construct Message objects.
    for m in messages:
        m.conversation_id = conversation_id
    session.add_all(messages)


async def add_extraction(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    input_text: str,
    extracted_json: dict,
    confidence: float | None,
    mode: str = "basic",
    input_type: str = "text",
) -> Extraction:
    e = Extraction(
        conversation_id=conversation_id,
        input_text=input_text,
        extracted_json=extracted_json,
        confidence=confidence,
        mode=mode,
        input_type=input_type,
        created_at=datetime.utcnow(),
    )
    session.add(e)
    await session.flush()
    return e


async def delete_conversation(session: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID) -> bool:
    conv = await get_conversation(session, user_id, conversation_id)
    if not conv:
        return False
    await session.delete(conv)
    return True

