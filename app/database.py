from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from app.config import settings


client = AsyncIOMotorClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)
try:
    # Attempt to get server information asynchronously
    conn = client.admin.command("ismaster")
    print(f'Connected to MongoDB {conn.get("version", "Unknown version")}')
except Exception as e:
    print(f"Unable to connect to the MongoDB server: {e}")

db = client[settings.MONGO_INITDB_DATABASE]
User = db.users
Event = db.events
Team = db.teams
Push_Token = db.push_token
# Creating an index asynchronously
# Add more async operations as needed
# Example: inserting a document
# await user_collection.insert_one({"email": "example@example.com", "name": "Example User"})
