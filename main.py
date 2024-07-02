from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.event import router as event_router
from app.routers.user import router as user_router
from app.routers.team import router as team_router
from app.tools.RabbitClient import RabbitClient
from app.service.FirebaseService import FirebaseService
from app.database import (
    connect_to_mongo,
    close_mongo_connection,
    get_initial_data,
    get_collection,
)
import os
from app.controller.BaseController import get_base_controller
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

        initial_data = await get_initial_data()
        self.rabbit_client = RabbitClient(
            rabbit_url=self.rabbit_url, push_token_service=push_token_service
        )
        await self.rabbit_client.start()  # Ensure RabbitMQ connection is started

        for team in initial_data:
            queue_name = f"team_{team['_id']}_queue"
            routing_keys = [
                f"team.{team['_id']}.event.*",
                f"team.{team['_id']}.notifications.*",
            ]
            await self.rabbit_client.declare_and_bind_queue(queue_name, routing_keys)
            await self.rabbit_client.start_consumer(queue_name)

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
#     notifications.router, tags=["Notifications"], prefix="/api/notifications"
# )


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
