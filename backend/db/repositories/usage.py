import uuid
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.usage import UsageTracking

async def increment_usage(
    db: AsyncSession,
    user_id: uuid.UUID,
    tokens_used: int = 0
) -> None:
    today = datetime.utcnow().date()
    # Find existing usage for today
    stmt = select(UsageTracking).where(
        UsageTracking.user_id == user_id,
        UsageTracking.usage_date == today
    )
    result = await db.execute(stmt)
    usage = result.scalars().first()

    if usage:
        usage.requests_count += 1
        usage.tokens_used += tokens_used
    else:
        new_usage = UsageTracking(
            user_id=user_id,
            tokens_used=tokens_used,
            requests_count=1,
            usage_date=today
        )
        db.add(new_usage)
    
    await db.commit()
