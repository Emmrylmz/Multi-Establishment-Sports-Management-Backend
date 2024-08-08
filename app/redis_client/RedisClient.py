from redis import asyncio as aioredis
from fastapi import FastAPI
import logging
from redis.exceptions import RedisError


class RedisClient:
    def __init__(self):
        self.redis = None
        self.logger = logging.getLogger(__name__)

    async def init_redis_pool(self, app: FastAPI):
        """Initialize Redis connection pool."""
        try:
            redis_url = app.state.redis_url
            self.redis = await aioredis.from_url(
                redis_url, encoding="utf-8", decode_responses=True
            )
            self.logger.info("Connected to Redis")
            app.state.redis = self.redis
        except RedisError as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            # You might want to raise an exception here or implement a retry mechanism

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            try:
                await self.redis.close()
                self.logger.info("Redis connection closed")
            except RedisError as e:
                self.logger.error(f"Error closing Redis connection: {str(e)}")

    async def _execute_redis_command(self, command, *args, **kwargs):
        """Execute a Redis command with error handling."""
        if not self.redis:
            self.logger.error("Redis client is not initialized")
            return None
        try:
            return await command(*args, **kwargs)
        except RedisError as e:
            self.logger.error(f"Redis error executing {command.__name__}: {str(e)}")
            return None

    async def get(self, key: str):
        """Get value from Redis."""
        return await self._execute_redis_command(self.redis.get, key)

    async def set(self, key: str, value: str, expire: int = None):
        """Set value in Redis."""
        if expire:
            return await self._execute_redis_command(
                self.redis.setex, key, expire, value
            )
        else:
            return await self._execute_redis_command(self.redis.set, key, value)

    async def delete(self, *keys):
        if not keys:
            return
        return await self._execute_redis_command(self.redis.delete, *keys)

    async def hget(self, name: str, key: str):
        """Get value from Redis hash."""
        return await self._execute_redis_command(self.redis.hget, name, key)

    async def hset(self, name: str, key: str, value: str):
        """Set value in Redis hash."""
        return await self._execute_redis_command(self.redis.hset, name, key, value)

    async def hdel(self, name: str, key: str):
        """Delete value from Redis hash."""
        return await self._execute_redis_command(self.redis.hdel, name, key)


redis_client = RedisClient()


def get_redis_client():
    return redis_client
