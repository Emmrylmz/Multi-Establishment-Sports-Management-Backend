# main.py

from fastapi import WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.event import router as event_router
from app.routers.user import router as user_router
from app.routers.note import router as notes_router
from app.routers.team import router as team_router
from app.routers.payment import router as payment_router
from app.routers.constants import router as constants_router
from app.database import (
    connect_to_mongo,
    close_mongo_connection,
)
from app.database import connect_to_mongo_sync
from app.main.main_app import FooApp


app = FooApp(
    rabbit_url=settings.RABBITMQ_URL,
    firebase_cred_path=settings.FIREBASE_CREDENTIALS_PATH,
    database_uri=settings.DATABASE_URL,
)

# Add rate limiting middleware
app.add_rate_limit_middleware()

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
    connect_to_mongo_sync()


@app.on_event("shutdown")
async def shutdown_event():
    await app.rabbit_client.close()
    print("RabbitMQ connection closed.")
    await close_mongo_connection()
