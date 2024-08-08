import redis
from app.config import settings
from contextlib import contextmanager


class SyncRedisClient:
    def __init__(self):
        self.redis = None

    def init_redis_pool(self):
        """Initialize Redis connection."""
        if self.redis is None:
            redis_url = settings.REDIS_URL
            self.redis = redis.from_url(
                redis_url, encoding="utf-8", decode_responses=True
            )
            print("connected to Redis", self.redis)
        return self.redis  # Return the redis connection

    def close(self):
        """Close Redis connection."""
        if self.redis:
            self.redis.close()

    def get(self, key: str):
        """Get value from Redis."""
        return self.redis.get(key)

    def set(self, key: str, value: str, expire: int = None):
        """Set value in Redis."""
        if expire:
            self.redis.setex(key, expire, value)
        else:
            self.redis.set(key, value)

    def delete(self, *keys):
        if not keys:
            return
        self.redis.delete(*keys)

    def hget(self, name: str, key: str):
        """Get value from Redis hash."""
        return self.redis.hget(name, key)

    def hset(self, name: str, key: str, value: str):
        """Set value in Redis hash."""
        self.redis.hset(name, key, value)

    def hdel(self, name: str, key: str):
        """Delete value from Redis hash."""
        self.redis.hdel(name, key)


sync_redis_client = SyncRedisClient()


@contextmanager
def get_sync_redis_client():
    redis_conn = sync_redis_client.init_redis_pool()
    try:
        yield redis_conn
    finally:
        pass
