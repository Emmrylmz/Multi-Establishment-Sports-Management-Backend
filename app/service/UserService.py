from fastapi import Depends, Query
from .. import utils
from datetime import datetime
from bson import ObjectId
from ..config import settings
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from ..service.MongoDBService import MongoDBService
from ..database import get_collection
from typing import List, Dict, Any, Optional
from ..redis_client import RedisClient


class UserService(MongoDBService):
    @classmethod
    async def create(cls, database: AsyncIOMotorDatabase, redis_client: RedisClient):
        self = cls.__new__(cls)
        await self.__init__(database, redis_client)
        return self

    async def __init__(self, database: AsyncIOMotorDatabase, redis_client: RedisClient):
        self.database = database
        self.redis_client = redis_client
        self.collection = await get_collection("User_Info", database)
        await super().__init__(self.collection)

    async def get_users_by_id(self, player_ids: List[str]) -> List[Dict[str, Any]]:
        cache_key = f"users_by_id:{','.join(sorted(player_ids))}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        object_ids = [ObjectId(id) for id in player_ids]
        cursor = self.collection.find(
            {"_id": {"$in": object_ids}},
            {"name": 1, "photo": 1, "_id": 1, "discount": 1},
        )

        user_infos = await cursor.to_list(length=None)

        # Convert ObjectId to string for JSON serialization
        for user in user_infos:
            user["_id"] = str(user["_id"])

        await self.redis_client.set(
            cache_key, user_infos, expire=300
        )  # Cache for 5 minutes
        return user_infos

    async def search_users_by_name(self, query: str) -> List[Dict[str, Any]]:
        cache_key = f"search_users:{query}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        pattern = f".*{query}.*"
        regex = {"$regex": pattern, "$options": "i"}

        users = await self.collection.find(
            {"name": regex}, {"_id": 1, "name": 1, "photo": 1}
        ).to_list(length=None)

        # Convert ObjectId to string for JSON serialization
        for user in users:
            user["_id"] = str(user["_id"])

        await self.redis_client.set(cache_key, users, expire=60)  # Cache for 1 minute
        return users

    async def update_user(self, user_id: str, update_data: dict) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_data}
        )

        # Invalidate caches
        await self.invalidate_user_caches(user_id)

        return result.modified_count > 0

    async def invalidate_user_caches(self, user_id: str):
        # Invalidate individual user cache
        await self.redis_client.delete(f"users_by_id:{user_id}")

        # Invalidate group user caches containing this user
        group_keys = await self.redis_client.keys(f"users_by_id:*{user_id}*")
        if group_keys:
            await self.redis_client.delete(*group_keys)

        # Invalidate search caches
        search_keys = await self.redis_client.keys("search_users:*")
        if search_keys:
            await self.redis_client.delete(*search_keys)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        cache_key = f"user:{user_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
            await self.redis_client.set(
                cache_key, user, expire=300
            )  # Cache for 5 minutes
        return user

    async def create_user(self, user_data: Dict[str, Any]) -> str:
        result = await self.collection.insert_one(user_data)
        user_id = str(result.inserted_id)

        # Invalidate relevant caches
        await self.invalidate_user_caches(user_id)

        return user_id

    async def delete_user(self, user_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})

        # Invalidate relevant caches
        await self.invalidate_user_caches(user_id)

        return result.deleted_count > 0

    async def get_users_by_criteria(
        self, criteria: Dict[str, Any], limit: int = 20, skip: int = 0
    ) -> List[Dict[str, Any]]:
        cache_key = (
            f"users_by_criteria:{hash(frozenset(criteria.items()))}:{limit}:{skip}"
        )
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        users = (
            await self.collection.find(criteria).skip(skip).limit(limit).to_list(None)
        )

        # Convert ObjectId to string for JSON serialization
        for user in users:
            user["_id"] = str(user["_id"])

        await self.redis_client.set(cache_key, users, expire=300)  # Cache for 5 minutes
        return users
