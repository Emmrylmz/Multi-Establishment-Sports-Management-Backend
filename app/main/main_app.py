# app/foo_app.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from ..service.TokenService import PushTokenService
from ..rabbit_client import RabbitClient
from ..service.FirebaseService import FirebaseService
from ..database import get_collection, connect_to_mongo
from ..celery_app.celery_setup import celery_app


class FooApp(FastAPI):
    def __init__(self, rabbit_url, firebase_cred_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbit_url = rabbit_url
        self.firebase_cred_path = firebase_cred_path
        self.rabbit_client = None
        self.firebase_service = None
        self.celery_app = celery_app.app

        # Set up rate limiter
        self.limiter = Limiter(key_func=get_remote_address)
        self.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    async def initialize_services(self):
        await connect_to_mongo()
        push_token_service = PushTokenService(collection=get_collection("Push_Token"))
        self.rabbit_client = RabbitClient(
            rabbit_url=self.rabbit_url, push_token_service=push_token_service
        )
        await self.rabbit_client.start()
        await self.rabbit_client.start_consumers()

        self.firebase_service = FirebaseService(self.firebase_cred_path)

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
                # Default limit
                limit = "1000/minute"

                # Adjust limit based on path
                if request.url.path.startswith("/api/auth"):
                    limit = "60/minute"  # More strict for auth endpoints
                elif request.url.path.startswith("/api"):
                    limit = "100/minute"  # For sensitive endpoints

                @self.limiter.limit(limit)
                async def _rate_limit_check(
                    request: Request,
                ):  # Add request parameter here
                    pass

                await _rate_limit_check(request)  # Pass request here
            except RateLimitExceeded:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, please try again later."},
                )

            response = await call_next(request)
            return response
