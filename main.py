from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware

# from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, user, notification, event


# from app.utils.websocket_manager import ConnectionManager
from app.tools.RabbitClient import RabbitClient

app = FastAPI()

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
url = "amqp://guest:guest@172.24.112.1:5672/"
rabbit_client = RabbitClient(url)

# Include routers for authentication and user management
app.include_router(auth.router, tags=["Auth"], prefix="/api/auth")
app.include_router(user.router, tags=["Users"], prefix="/api/users")
app.include_router(notification.trigger)
app.include_router(event.router, tags=["events"], prefix="/events")
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
    await rabbit_client.start()
    # await rabbit_client.start_consumer()


@app.on_event("shutdown")
async def shutdown_event():
    # Close RabbitMQ connection
    await rabbit_client.close()
    print("RabbitMQ connection closed.")


# Add the RabbitMQ response handling logic here if needed
