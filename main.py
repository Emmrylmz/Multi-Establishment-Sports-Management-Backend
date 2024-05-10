from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, user, notification, event, team
from app.tools.RabbitClient import RabbitClient
import logging

class FooApp(FastAPI):
    def __init__(self, rabbit_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbit_client = RabbitClient(rabbit_url=rabbit_url)

url = "amqp://guest:guest@0.0.0.0:5672//"
app = FooApp(rabbit_url=url)

# Setup CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, tags=["Auth"], prefix="/api/auth")
app.include_router(user.router, tags=["Users"], prefix="/api/users")
app.include_router(event.router, tags=["events"], prefix="/api/events")
app.include_router(team.router, tags=["teams"], prefix="/api/teams")

# Setup logging
logging.basicConfig(level=logging.INFO)

@app.on_event("startup")
async def startup_event():
    try:
        await app.rabbit_client.connect()
        logging.info("RabbitMQ connection started.")
    except Exception as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await app.rabbit_client.close()
        logging.info("RabbitMQ connection closed.")
    except Exception as e:
        logging.error(f"Failed to close RabbitMQ connection: {e}")








"""
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
import asyncio
from app.config import settings
from app.routers import auth, notification, event, team
=======
from app.routers import auth, user, notification, event, team
>>>>>>> rabbit_stann
from app.tools.RabbitClient import RabbitClient
from app.service.FirebaseService import FirebaseService
from app.tools.ExponentServerSDK import PushMessage, push_client

# may use dependencies
from app.config import settings

class FooApp(FastAPI):
    def __init__(self, rabbit_url, firebase_cred_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbit_client = RabbitClient(rabbit_url=rabbit_url)
<<<<<<< HEAD
        self.firebase_service = FirebaseService(firebase_cred_path)
=======

    @classmethod
    def log_incoming_message(cls, message: dict):
        "Method to do something meaningful with the incoming message" # here is three quotes
        # logger.info("Here we got incoming message %s", message)
>>>>>>> rabbit_stann


<<<<<<< HEAD
url = "amqp://guest:guest@localhost:5672//"
app = FooApp(rabbit_url=url)
=======
path = r"C:\Users\emmry\OneDrive\Masaüstü\DACKA-App\server\app-fastapi\app\service\firbaseKey.json"

url = "amqp://guest:guest@localhost:5672//"
app = FooApp(
    rabbit_url=url,
    firebase_cred_path=path,
    database_uri=settings.DATABASE_URL,
)
>>>>>>> 23d66e1 (from rabbit mq queue to expo notification service)

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
<<<<<<< HEAD
app.include_router(notification.router)
=======
app.include_router(user.router, tags=["Users"], prefix="/api/users")
>>>>>>> rabbit_stann
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
<<<<<<< HEAD
<<<<<<< HEAD
    print("RabbitMQ connection started.")
    # await rabbit_client.start_subscription()
=======
>>>>>>> f801e6c (latest)
=======
    await app.rabbit_client.start_subscription("emir")
>>>>>>> 23d66e1 (from rabbit mq queue to expo notification service)


@app.on_event("shutdown")
async def shutdown_event():
    # Close RabbitMQ connection
    # stannsey
    await rabbit_client.close()
    print("RabbitMQ connection closed.")
<<<<<<< HEAD
=======


# Add the RabbitMQ response handling logic here if needed
"""
>>>>>>> rabbit_stann
