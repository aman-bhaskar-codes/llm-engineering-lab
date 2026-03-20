import time
from fastapi import HTTPException, status, Depends
from loguru import logger
from api.deps import get_current_user_id
from core.redis import redis_manager

RATE_LIMIT_PREFIX = "ratelimit:"
# Default limit: 60 requests per 60 seconds
DEFAULT_LIMIT = 60
WINDOW = 60

async def check_rate_limit(
    user_id: str = Depends(get_current_user_id),
    limit: int = DEFAULT_LIMIT,
    window: int = WINDOW
) -> None:
    """
    Sliding window rate limiter using Redis sorted sets.
    """
    client = redis_manager.get_client()
    if not client:
        # Graceful degradation: let request through if Redis is down
        return

    key = f"{RATE_LIMIT_PREFIX}{user_id}"
    now = time.time()
    
    try:
        # Use a pipeline for atomicity
        async with client.pipeline(transaction=True) as pipe:
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, now - window)
            # Count remaining entries
            pipe.zcard(key)
            # Add current entry
            pipe.zadd(key, {str(now): now})
            # Set TTL for the key
            pipe.expire(key, window)
            
            _, count, _, _ = await pipe.execute()
            
            if count >= limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Fail open
