from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from fastapi import Depends, Request
from functools import lru_cache
from app.config import settings


async def get_mongo_client(request: Request) -> AsyncIOMotorClient:
    return request.app.mongodb_client


async def get_database(
    client: AsyncIOMotorClient = Depends(get_mongo_client),
) -> AsyncIOMotorDatabase:
    return client[settings.MONGO_INITDB_DATABASE]


async def get_collection(
    collection_name: str, db: AsyncIOMotorDatabase = Depends(get_database)
) -> AsyncIOMotorCollection:
    return db[collection_name]


async def ensure_indexes(db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        await db.Payment.create_index(
            [("user_id", 1), ("due_date", 1), ("status", 1)], background=True
        )
        await db.Payment.create_index(
            [("payment_type", 1), ("due_date", 1), ("status", 1)], background=True
        )
        await db.Attendance.create_index("event_id")
        await db.Attendance.create_index("timestamp")
        await db.Auth.create_index("email")
        await db.Team.create_index("team_id")

        print("Indexes ensured successfully")
    except Exception as e:
        print(f"Error ensuring indexes: {e}")
        raise


# You can call this function during app startup
async def initialize_database(db: AsyncIOMotorDatabase = Depends(get_database)):
    await ensure_indexes(db)
