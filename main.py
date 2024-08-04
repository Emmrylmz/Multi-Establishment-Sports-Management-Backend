# main.py

import cProfile
import io
import pstats
import time
from fastapi import Request, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.event import router as event_router
from app.routers.user import router as user_router
from app.routers.note import router as notes_router
from app.routers.team import router as team_router
from app.routers.payment import router as payment_router
from app.routers.constants import router as constants_router
from app.main.main_app import FooApp


class ProfilingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        profiler = cProfile.Profile()
        profiler.enable()
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        profiler.disable()

        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(20)

        print(f"Request to {request.url} took {process_time:.2f} seconds")
        print(s.getvalue())

        return response


app = FooApp(
    rabbit_url="amqp://guest:guest@rabbitmq:5672/",
    firebase_cred_path="app/service/firebaseKey.json",
    database_uri="mongodb+srv://banleue13:Mrfadeaway.1@cluster0.lvzd0dt.mongodb.net/?retryWrites=true&w=majority",
    redis_url="redis://redis:6379/0",
)

# Add profiler middleware if in debug mode
# app.add_middleware(ProfilingMiddleware)

# Add rate limiting middleware
# app.add_rate_limit_middleware()

# CORS setup
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, tags=["Auth"], prefix="/api/auth")
app.include_router(event_router, tags=["events"], prefix="/api/events")
app.include_router(team_router, tags=["teams"], prefix="/api/teams")
app.include_router(user_router, tags=["user_info"], prefix="/api/user_info")
app.include_router(payment_router, tags=["payments"], prefix="/api/payments")
app.include_router(constants_router, tags=["constants"], prefix="/api/constants")
app.include_router(notes_router, tags=["notes"], prefix="/api/notes")


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    await app.initialize_services()


@app.on_event("shutdown")
async def shutdown_event():
    await app.rabbit_client.stop()
    print("RabbitMQ connection closed.")
