from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from app.config import settings


db = AsyncIOMotorClient(
    "mongodb+srv://banleue13:Mrfadeaway.1@cluster0.lvzd0dt.mongodb.net/?retryWrites=true&w=majority",
    serverSelectionTimeoutMS=5000,
)
try:
    # Attempt to get server information asynchronously
    conn = db.admin.command("ismaster")
    print(f'Connected to MongoDB {conn.get("version", "Unknown version")}')
except Exception as e:
    print(f"Unable to connect to the MongoDB server: {e}")

# db = client[settings.MONGO_INITDB_DATABASE]
Auth = db.auth
Event = db.events
Team = db.teams
Push_Token = db.push_token
User_Info = db.user_info
# Creating an index asynchronously
# Add more async operations as needed
# Example: inserting a document
# await user_collection.insert_one({"email": "example@example.com", "name": "Example User"})
