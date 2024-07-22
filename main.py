from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.event import router as event_router
from app.routers.user import router as user_router
from app.routers.team import router as team_router
from app.routers.payment import router as payment_router
from app.routers.constants import router as constants_router
from app.tools.RabbitClient import RabbitClient
from app.service.FirebaseService import FirebaseService
from app.database import (
    connect_to_mongo,
    close_mongo_connection,
    get_collection,
)
import os
from app.service.TokenService import PushTokenService


class FooApp(FastAPI):
    def __init__(self, rabbit_url, firebase_cred_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbit_url = rabbit_url
        self.firebase_cred_path = firebase_cred_path
        self.rabbit_client = None
        self.firebase_service = None

    async def initialize_services(self):
        await connect_to_mongo()
        push_token_service = PushTokenService(collection=get_collection("Push_Token"))

        self.rabbit_client = RabbitClient(
            rabbit_url=self.rabbit_url, push_token_service=push_token_service
        )
        await self.rabbit_client.start()  # Ensure RabbitMQ connection is started
        await self.rabbit_client.start_consumers()

        self.firebase_service = FirebaseService(self.firebase_cred_path)


url = settings.RABBITMQ_URL
app = FooApp(
    rabbit_url=url,
    firebase_cred_path=settings.FIREBASE_CREDENTIALS_PATH,
    database_uri=settings.DATABASE_URL,
)

# CORS setup
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specify actual methods used
    allow_headers=["*"],
)


app.include_router(auth_router, tags=["Auth"], prefix="/api/auth")
# app.include_router(notification.router)
app.include_router(event_router, tags=["events"], prefix="/api/events")
app.include_router(team_router, tags=["teams"], prefix="/api/teams")
app.include_router(user_router, tags=["user_info"], prefix="/api/user_info")
app.include_router(payment_router, tags=["payments"], prefix="/api/payments")
app.include_router(constants_router, tags=["constants"], prefix="/api/constants")


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    await app.initialize_services()


@app.on_event("shutdown")
async def shutdown_event():
    # Close RabbitMQ connection
    await rabbit_client.close()
    print("RabbitMQ connection closed.")
    await close_mongo_connection()
