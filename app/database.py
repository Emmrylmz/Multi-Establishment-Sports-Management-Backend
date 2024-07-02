from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from .config import settings
from fastapi import Depends


class Database:
    client: AsyncIOMotorClient = None


db = Database()


async def connect_to_mongo():
    url = settings.DATABASE_URL
    db.client = AsyncIOMotorClient(
        url,
        serverSelectionTimeoutMS=5000,
    )
    try:
        # Asynchronously get server information
        await db.client.admin.command("ismaster")
        print(f"Connected to MongoDB")
    except Exception as e:
        print(f"Unable to connect to the MongoDB server: {e}")

    return db


async def get_initial_data() -> list:
    collection = get_collection(
        "Team"
    )  # Ensure this matches your actual collection name
    initial_data = await collection.find({}, {"_id": 1}).to_list(
        length=None
    )  # Fetch up to 100 documents, adjust as needed
    return initial_data


async def close_mongo_connection():
    db.client.close()


def get_database():
    if db.client is None:
        raise Exception(
            "Database client is not initialized. Call `connect_to_mongo` first."
        )
    return db.client[settings.MONGO_INITDB_DATABASE]


def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    db = get_database()
    return db[collection_name]

    # db = client[settings.MONGO_INITDB_DATABASE]
    # Auth = db.auth
    # Event = db.events
    # Team = db.teams
    # Push_Token = db.push_token
    # User_Info = db.user_info


# Creating an index asynchronously
# Add more async operations as needed
# Example: inserting a document
# await user_collection.insert_one({"email": "example@example.com", "name": "Example User"})
