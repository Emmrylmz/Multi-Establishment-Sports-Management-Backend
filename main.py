from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.config import settings
from app.routers import auth, user, notification, event, team
from app.tools.RabbitClient import RabbitClient


class FooApp(FastAPI):
    def __init__(self, rabbit_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbit_client = RabbitClient(rabbit_url=rabbit_url)

    @classmethod
    def log_incoming_message(cls, message: dict):
        """Method to do something meaningful with the incoming message"""
        # logger.info("Here we got incoming message %s", message)


url = "amqp://guest:guest@localhost:5672//"
app = FooApp(rabbit_url=url)

# CORS setup
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specify actual methods used
    allow_headers=["*"],
)

# Static files for documentation and other purposes
# app.mount("/static", StaticFiles(directory="path/to/static"), name="static")

# Connection Manager for WebSocket
# manager = ConnectionManager()

# RabbitMQ Client Setup
# rabbit_client = RabbitClient(
#     rabbit_url=url,
#     service="notification",
#     # incoming_message_handler=your_message_handler_function  # Define this function to handle incoming messages
# )
# Include routers for authentication and user management
app.include_router(auth.router, tags=["Auth"], prefix="/api/auth")
app.include_router(user.router, tags=["Users"], prefix="/api/users")
app.include_router(notification.trigger)
app.include_router(event.router, tags=["events"], prefix="/api/events")
app.include_router(team.router, tags=["teams"], prefix="/api/teams")
#     notifications.router, tags=["Notifications"], prefix="/api/notifications"
# )


# WebSocket Endpoint for real-time notifications
# @app.websocket("/ws/{user_id}")
# async def websocket_endpoint(websocket: WebSocket, user_id: int):
#     await manager.connect(websocket, user_id)
#     try:
#         while True:
#             data = await websocket.receive_text()
#             await manager.send_personal_message({"user_id": user_id, "message": data})
#     except Exception as e:
#         print(e)
#     finally:
#         await manager.disconnect(user_id)


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    # Connect to RabbitMQ
    # app.pika_client = PikaClient()  # Ensure you initialize this correctly

    await app.rabbit_client.start()
<<<<<<< HEAD
    print("RabbitMQ connection started.")
    # await rabbit_client.start_subscription()
=======
>>>>>>> f801e6c (latest)


@app.on_event("shutdown")
async def shutdown_event():
    # Close RabbitMQ connection
    # stannsey
    await rabbit_client.close()
    print("RabbitMQ connection closed.")
