from redis import asyncio as aioredis
from fastapi import FastAPI


class RedisClient:
    def __init__(self):
        self.redis = None

    async def init_redis_pool(self, app: FastAPI):
        """Initialize Redis connection pool."""
        redis_url = app.state.redis_url
        self.redis = await aioredis.from_url(
            redis_url, encoding="utf-8", decode_responses=True
        )
        print("connected to Redis", self.redis)
        app.state.redis = self.redis

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str):
        """Get value from Redis."""
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: int = None):
        """Set value in Redis."""
        if expire:
            await self.redis.setex(key, expire, value)
        else:
            await self.redis.set(key, value)

    async def delete(self, key: str):
        """Delete value from Redis."""
        await self.redis.delete(key)

    async def hget(self, name: str, key: str):
        """Get value from Redis hash."""
        return await self.redis.hget(name, key)

    async def hset(self, name: str, key: str, value: str):
        """Set value in Redis hash."""
        await self.redis.hset(name, key, value)

    async def hdel(self, name: str, key: str):
        """Delete value from Redis hash."""
        await self.redis.hdel(name, key)


redis_client = RedisClient()


def get_redis_client():
    return redis_client
