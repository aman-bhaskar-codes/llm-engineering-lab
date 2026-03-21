import json
import hashlib
from typing import Any
from loguru import logger
from core.redis import redis_manager

def generate_cache_key(input_text: str, mode: str, schema: dict = None) -> str:
    """Generate a stable cache key based on input, mode, and schema."""
    schema_str = json.dumps(schema, sort_keys=True) if schema else ""
    content = f"{input_text}:{mode}:{schema_str}".encode("utf-8")
    return f"extract:cache:{hashlib.sha256(content).hexdigest()}"

async def cache_get(key: str) -> Any | None:
    client = redis_manager.get_client()
    if not client:
        return None
    try:
        data = await client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis cache_get failed: {e}")
    return None

async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    client = redis_manager.get_client()
    if not client:
        return
    try:
        await client.set(key, json.dumps(value), ex=ttl)
    except Exception as e:
        logger.warning(f"Redis cache_set failed: {e}")
