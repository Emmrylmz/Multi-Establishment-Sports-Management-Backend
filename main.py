from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.config import settings
from app.routers import auth, notification, event, team
from app.tools.RabbitClient import RabbitClient
from app.service.FirebaseService import FirebaseService
from app.tools.ExponentServerSDK import PushMessage, push_client


class FooApp(FastAPI):
    def __init__(self, rabbit_url, firebase_cred_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbit_client = RabbitClient(rabbit_url=rabbit_url)
        self.firebase_service = FirebaseService(firebase_cred_path)


path = r"/Users/stannisozbov/Documents/pearl/AirballAI/APP/app-fastapi/app/service/firbaseKey.json"

url = "amqp://guest:guest@localhost:5672//"

app = FooApp(
    rabbit_url=url,
    firebase_cred_path=path,
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


app.include_router(auth.router, tags=["Auth"], prefix="/api/auth")
app.include_router(notification.router)
app.include_router(event.router, tags=["events"], prefix="/api/events")
app.include_router(team.router, tags=["teams"], prefix="/api/teams")
#     notifications.router, tags=["Notifications"], prefix="/api/notifications"
# )


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():

    # Connect to RabbitMQ
    # app.pika_client = PikaClient()  # Ensure you initialize this correctly
    app.firebase_service.init_firebase()
    await app.rabbit_client.start()
    # await app.rabbit_client.start_subscription("emir")


@app.on_event("shutdown")
async def shutdown_event():
    # Close RabbitMQ connection
    # stannsey
    await rabbit_client.close()
    print("RabbitMQ connection closed.")
