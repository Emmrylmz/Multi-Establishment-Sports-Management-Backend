# repositories/auth_repository.py

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Dict, Optional, Any
from pymongo.client_session import ClientSession
from ..database import get_collection
from ..models import user_schemas


class AuthRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = None

    @classmethod
    async def initialize(cls, database: AsyncIOMotorDatabase):
        self = cls(database)
        self.collection = await get_collection("Auth", database)
        self.deleted_user_collection = await get_collection("Deleted_User", database)
        return self

    async def create_user(
        self, user_data: Dict[str, Any], session: Optional[ClientSession] = None
    ) -> Dict[str, Any]:
        result = await self.collection.insert_one(user_data, session=session)
        user_data["_id"] = result.inserted_id
        return user_data

    async def find_user_by_email(
        self, email: str, session: Optional[ClientSession] = None
    ) -> Optional[Dict[str, Any]]:
        user = await self.collection.find_one({"email": email}, session=session)
        return user

    async def insert_user(
        self, user_data: Dict[str, Any], session: Optional[ClientSession] = None
    ) -> Dict[str, Any]:
        result = await self.collection.insert_one(user_data, session=session)
        user_data["_id"] = result.inserted_id
        return user_data

    async def get_user_by_id(
        self, user_id: ObjectId, session: Optional[ClientSession] = None
    ) -> Optional[Dict[str, Any]]:
        user = await self.collection.find_one({"_id": user_id}, session=session)
        return user

    async def delete_user(
        self, user: user_schemas.User, session: Optional[ClientSession] = None
    ) -> Dict[str, Any]:
        response_insert = await self.deleted_user_collection.insert_one(
            user, session=session
        )
        user_id = user["_id"]

        response_delete = await self.collection.delete_one(
            {"_id": ObjectId(user_id)}, session=session
        )
        return response_delete, response_insert

    async def update_user(
        self,
        user_id: ObjectId,
        update_data: Dict[str, Any],
        session: Optional[ClientSession] = None,
    ) -> Dict[str, Any]:
        result = await self.collection.update_one(
            {"_id": user_id}, {"$set": update_data}, session=session
        )
        return {"modified_count": result.modified_count}

    # Add other methods as needed, such as storing refresh tokens, etc.
