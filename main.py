from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.auth import auth_router
from app.routers.event import event_router
from app.routers.team import team_router
from app.routers.user import user_router
from app.tools.RabbitClient import RabbitClient
from app.service.FirebaseService import FirebaseService
import os


class FooApp(FastAPI):
    def __init__(self, rabbit_url, firebase_cred_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbit_client = RabbitClient(rabbit_url=rabbit_url)
        self.firebase_service = FirebaseService(firebase_cred_path)


url = "amqp://guest:guest@rabbitmq:5672/"
app = FooApp(
    rabbit_url=url,
    firebase_cred_path="app/service/firebaseKey.json",
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
    # Connect to RabbitMQ
    app.firebase_service.init_firebase()
    await app.rabbit_client.start()
    await app.rabbit_client.declare_and_bind_queue(
        queue_name="664b346f904d48bc59f606b8",
        routing_keys=["team.663be0c3b6f73eaa9b08b048.event.*"],
    )
    await app.rabbit_client.start_consumer("664b346f904d48bc59f606b8")


@app.on_event("shutdown")
async def shutdown_event():
    # Close RabbitMQ connection
    await rabbit_client.close()
    print("RabbitMQ connection closed.")
