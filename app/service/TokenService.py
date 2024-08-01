import logging
from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from ..models.firebase_token_schemas import PushTokenSchema
from .MongoDBService import MongoDBService
from ..database import get_collection, get_database
from ..redis_client import RedisClient
from typing import List, Optional


class PushTokenService(MongoDBService):
    @classmethod
    async def create(cls, database: AsyncIOMotorDatabase, redis_client: RedisClient):
        self = cls.__new__(cls)
        await self.__init__(database, redis_client)
        return self

    async def __init__(self, database: AsyncIOMotorDatabase, redis_client: RedisClient):
        self.database = database
        self.redis_client = redis_client
        self.collection = await get_collection("PushToken", database)
        self.team_collection = await get_collection("Team", database)
        await super().__init__(self.collection)

    async def save_token(self, payload: PushTokenSchema, user_id: str) -> bool:
        try:
            data = payload.dict()
            token = await self.collection.find_one({"_id": ObjectId(user_id)})
            if token:
                res = await self.collection.update_one(
                    {"_id": ObjectId(user_id)}, {"$set": {"token": payload.token}}
                )
                success = res.modified_count > 0
            else:
                data["_id"] = ObjectId(user_id)
                result = await self.collection.insert_one(data)
                success = result.inserted_id is not None

            if success:
                await self.invalidate_user_token_cache(user_id)
                await self.invalidate_all_tokens_cache()
                await self.invalidate_province_tokens_cache(data.get("province"))
            return success
        except Exception as e:
            logging.error(f"Error saving token: {e}")
            return False

    async def get_team_player_tokens(self, team_id: str) -> List[str]:
        cache_key = f"team_player_tokens:{team_id}"
        cached_tokens = await self.redis_client.get(cache_key)
        if cached_tokens:
            return cached_tokens

        try:
            team = await self.team_collection.find_one({"_id": ObjectId(team_id)})
            if team:
                players_ids = team.get("team_players", [])
                object_ids = [ObjectId(id) for id in players_ids]
                query = {"_id": {"$in": object_ids}}
                documents = await self.collection.find(query, {"token": 1}).to_list(
                    None
                )
                tokens = [
                    player.get("token") for player in documents if player.get("token")
                ]

                await self.redis_client.set(
                    cache_key, tokens, expire=3600
                )  # Cache for 1 hour
                return tokens
            else:
                logging.warning(f"Team not found: {team_id}")
                return []
        except Exception as e:
            logging.error(f"Error getting team player tokens: {e}")
            return []

    async def get_user_token(self, user_id: str) -> Optional[str]:
        cache_key = f"user_token:{user_id}"
        cached_token = await self.redis_client.get(cache_key)
        if cached_token:
            return cached_token

        try:
            token = await self.collection.find_one(
                {"_id": ObjectId(user_id)}, {"token": 1}
            )
            if not token:
                logging.warning(f"No user Push Token found for user: {user_id}")
                return None
            user_token = token.get("token")
            if user_token:
                await self.redis_client.set(
                    cache_key, user_token, expire=3600
                )  # Cache for 1 hour
            return user_token
        except Exception as e:
            logging.error(f"Error getting user token: {e}")
            return None

    async def get_all_user_tokens(self) -> List[str]:
        cache_key = "all_user_tokens"
        cached_tokens = await self.redis_client.get(cache_key)
        if cached_tokens:
            return cached_tokens

        try:
            documents = await self.collection.find({}, {"token": 1, "_id": 0}).to_list(
                None
            )
            tokens = [doc.get("token") for doc in documents if doc.get("token")]
            await self.redis_client.set(
                cache_key, tokens, expire=3600
            )  # Cache for 1 hour
            return tokens
        except Exception as e:
            logging.error(f"Error getting all user tokens: {e}")
            return []

    async def get_province_user_tokens(self, province: str) -> List[str]:
        cache_key = f"province_user_tokens:{province}"
        cached_tokens = await self.redis_client.get(cache_key)
        if cached_tokens:
            return cached_tokens

        try:
            query = {"province": province}
            documents = await self.collection.find(
                query, {"token": 1, "_id": 0}
            ).to_list(None)
            tokens = [doc.get("token") for doc in documents if doc.get("token")]
            await self.redis_client.set(
                cache_key, tokens, expire=3600
            )  # Cache for 1 hour
            return tokens
        except Exception as e:
            logging.error(f"Error getting province user tokens: {e}")
            return []

    async def invalidate_user_token_cache(self, user_id: str):
        await self.redis_client.delete(f"user_token:{user_id}")

    async def invalidate_all_tokens_cache(self):
        await self.redis_client.delete("all_user_tokens")

    async def invalidate_province_tokens_cache(self, province: str):
        if province:
            await self.redis_client.delete(f"province_user_tokens:{province}")

    async def invalidate_team_player_tokens_cache(self, team_id: str):
        await self.redis_client.delete(f"team_player_tokens:{team_id}")
