from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# from service.TokenService import PushTokenService
from app.rabbit_client import RabbitClient

from app.service.FirebaseService import FirebaseService
from app.database import ensure_indexes
from app.celery_app.celery_setup import celery_app
from functools import wraps
from app.redis_client.RedisClient import redis_client
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


@asynccontextmanager
async def lifespan(app: "FooApp"):
    # Startup
    await app.initialize_database()

    await ensure_indexes(app.mongodb)
    # Initialize other services
    await app.initialize_external_services()

    yield

    # Shutdown
    app.mongodb_client.close()
    await app.close_services()


class FooApp(FastAPI):
    def __init__(self, rabbit_url, firebase_cred_path, redis_url, *args, **kwargs):
        super().__init__(*args, **kwargs, lifespan=lifespan)
        self.rabbit_url = rabbit_url
        self.firebase_cred_path = firebase_cred_path
        self.redis_url = redis_url
        self.rabbit_client = None
        self.firebase_service = None
        self.redis_client = redis_client
        self.celery_app = celery_app.app

        # Set up rate limiter
        self.limiter = Limiter(key_func=get_remote_address)
        self.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    async def initialize_database(self):
        # Initialize MongoDB and Redis clients
        client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=200,
            minPoolSize=10,
            maxIdleTimeMS=60000,
            waitQueueTimeoutMS=30000,
        )
        self.mongodb_client = client
        self.mongodb = client[settings.MONGO_INITDB_DATABASE]

    async def initialize_external_services(self):
        # self.push_token_service = await PushTokenService.create(
        #     self.mongodb, self.redis_client
        # )
        self.push_token_service = None
        self.rabbit_client = RabbitClient(
            rabbit_url=self.rabbit_url, push_token_service=self.push_token_service
        )
        await self.rabbit_client.start()
        await self.rabbit_client.start_consumers()

        await FirebaseService.initialize(self.firebase_cred_path)

        # Initialize Redis connection
        self.state.redis_url = self.redis_url
        await self.redis_client.init_redis_pool(self)

    async def close_services(self):
        await self.redis_client.close()
        if self.rabbit_client:
            await self.rabbit_client.stop()

    @property
    def limiter(self):
        return self._limiter

    @limiter.setter
    def limiter(self, limiter):
        self._limiter = limiter
        self.state.limiter = limiter

    def add_rate_limit_middleware(self):
        @self.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            try:
                limit = "10000/minute"
                if request.url.path.startswith("/api/auth"):
                    limit = "1000/minute"
                elif request.url.path.startswith("/api"):
                    limit = "10000/minute"

                @self.limiter.limit(limit)
                async def _rate_limit_check(request: Request):
                    pass

                await _rate_limit_check(request)
            except RateLimitExceeded:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, please try again later."},
                )

            response = await call_next(request)
            return response

    def cached(self, ttl=300, key_prefix=""):
        def wrapper(func):
            @wraps(func)
            async def wrapped(*args, **kwargs):
                key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
                cached_result = await self.redis_client.get(key)
                if cached_result is not None:
                    return cached_result
                result = await func(*args, **kwargs)
                await self.redis_client.set(key, result, expire=ttl)
                return result

            return wrapped

        return wrapper

    def invalidate_cache(self, key_prefix=""):
        async def invalidator():
            keys = await self.redis_client.keys(f"{key_prefix}*")
            if keys:
                for key in keys:
                    await self.redis_client.delete(key)

        return invalidator
