from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from .config import settings
from fastapi import Depends


class Database:
    client: AsyncIOMotorClient = None

    async def ensure_indexes(self):
        try:
            db = self.client[settings.MONGO_INITDB_DATABASE]

            # Create indexes for the tickets collection
            await db.Payment.create_index(
                [("user_id", 1), ("due_date", 1), ("status", 1)], background=True
            )
            await db.Payment.create_index(
                [("payment_type", 1), ("due_date", 1), ("status", 1)], background=True
            )
            print("Indexes ensured successfully")
        except OperationFailure as e:
            print(f"Error ensuring indexes: {e}")


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
        await db.ensure_indexes()
    except Exception as e:
        print(f"Unable to connect to the MongoDB server: {e}")

    return db


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
