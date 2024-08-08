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
    async def initialize(
        cls, database: AsyncIOMotorDatabase, redis_client: RedisClient
    ):
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
                invalidate_caches.delay(["all_user_tokens", f"user_token:{user_id}"])
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
            pipeline = [
                {"$match": {"_id": ObjectId(team_id)}},
                {
                    "$lookup": {
                        "from": "Push_Token",  # Assuming the players collection name
                        "localField": "team_players",
                        "foreignField": "_id",
                        "as": "players",
                    }
                },
                {
                    "$project": {
                        "tokens": {
                            "$filter": {
                                "input": "$players.token",
                                "as": "token",
                                "cond": {"$ne": ["$$token", None]},
                            }
                        }
                    }
                },
            ]

            result = await self.team_collection.aggregate(pipeline).to_list(1)

            if result:
                tokens = result[0].get("tokens", [])
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
