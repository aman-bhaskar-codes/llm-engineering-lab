from typing import AsyncGenerator
from redis.asyncio import Redis, from_url
from core.config import settings
from loguru import logger

class RedisManager:
    def __init__(self, url: str):
        self.url = url
        self.client: Redis | None = None

    async def connect(self) -> None:
        if not self.client:
            try:
                self.client = from_url(self.url, decode_responses=True)
                await self.client.ping()
                logger.info("Connected to Redis successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.client = None

    async def disconnect(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Disconnected from Redis.")

    def get_client(self) -> Redis | None:
        return self.client

redis_manager = RedisManager(settings.redis_url)

async def get_redis() -> AsyncGenerator[Redis | None, None]:
    yield redis_manager.get_client()
