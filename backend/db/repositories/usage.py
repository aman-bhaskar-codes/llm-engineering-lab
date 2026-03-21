import uuid
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.usage import UsageTracking
from fastapi import HTTPException

async def check_and_increment_quota(db: AsyncSession, user_id: uuid.UUID, plan: str = "free") -> None:
    today = datetime.utcnow().date()
    limit = 50 if plan == "free" else 5000 
    
    stmt = select(UsageTracking).where(
        UsageTracking.user_id == user_id,
        UsageTracking.usage_date == today
    )
    result = await db.execute(stmt)
    usage = result.scalars().first()
    
    if usage and usage.requests_count >= limit:
        raise HTTPException(
            status_code=402, 
            detail=f"Daily extraction limit ({limit}) reached for {plan} plan."
        )
        
    if usage:
        usage.requests_count += 1
    else:
        new_usage = UsageTracking(
            user_id=user_id,
            tokens_used=0,
            requests_count=1,
            usage_date=today
        )
        db.add(new_usage)
    
    await db.commit()
