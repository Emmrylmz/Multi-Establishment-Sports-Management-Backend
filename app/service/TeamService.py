from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from fastapi import Depends, HTTPException, status
from ..database import get_collection
from .MongoDBService import MongoDBService
from ..utils import ensure_object_id
from pymongo.errors import PyMongoError
from bson import ObjectId
from typing import List, Dict, Any, Optional
from aiocache import cached
from aiocache.serializers import PickleSerializer
from ..redis_client import RedisClient
from ..models.user_schemas import UserRole
from app.celery_app.celery_tasks import invalidate_caches
import json


class TeamService(MongoDBService):
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
        self.collection = await get_collection("Team", database)
        self.auth_collection = await get_collection("Auth", database)
        await super().__init__(self.collection)

    async def add_users_to_teams(
        self, user_ids, team_ids, user_role_field, register=True
    ):
        try:
            async with await self.collection.database.client.start_session() as session:
                async with session.start_transaction():
                    teams_update_result = await self.collection.update_many(
                        {"_id": {"$in": team_ids}},
                        {"$addToSet": {user_role_field: {"$each": user_ids}}},
                        session=session,
                    )

                    users_update_result = None
                    if not register:
                        users_update_result = await self.auth_collection.update_many(
                            {"_id": {"$in": user_ids}},
                            {"$addToSet": {"teams": {"$each": team_ids}}},
                            session=session,
                        )

                    if teams_update_result.modified_count > 0 and (
                        register
                        or (
                            users_update_result
                            and users_update_result.modified_count > 0
                        )
                    ):
                        cache_keys = [f"team_users:{tid}" for tid in team_ids] + [
                            f"teams_by_id:{','.join(map(str, team_ids))}",
                            "all_teams",
                            f"team_coaches:{','.join(map(str, team_ids))}",
                        ]
                        invalidate_caches.delay(str(team_ids))
                        return {
                            "status": "success",
                            "modified_count_teams": teams_update_result.modified_count,
                            "modified_count_users": (
                                users_update_result.modified_count
                                if users_update_result
                                else 0
                            ),
                        }
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Failed to add users to some or all teams or update users with teams.",
                        )
        except PyMongoError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transaction failed: {str(e)}",
            )

    async def get_team_users_by_id(
        self, team_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        cache_key = f"team_users:{team_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        pipeline = [
            {"$match": {"_id": ObjectId(team_id)}},
            {
                "$lookup": {
                    "from": "User_Info",
                    "let": {"player_ids": "$team_players"},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$_id", "$$player_ids"]}}},
                        {
                            "$project": {
                                "name": 1,
                                "photo": 1,
                                "discount": 1,
                            }
                        },
                    ],
                    "as": "player_infos",
                }
            },
            {
                "$lookup": {
                    "from": "User_Info",
                    "let": {"coach_ids": "$team_coaches"},
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$_id", "$$coach_ids"]}}},
                        {
                            "$project": {
                                "name": 1,
                                "photo": 1,
                                "discount": 1,
                                "discount_reason": 1,
                            }
                        },
                    ],
                    "as": "coach_infos",
                }
            },
            {"$project": {"player_infos": 1, "coach_infos": 1}},
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        team_data = results[0] if results else {"player_infos": [], "coach_infos": []}

        await self.redis_client.set(cache_key, team_data, expire=300)
        return team_data

    async def check_team_exists(self, team_id):
        team_id = ensure_object_id(team_id)
        cache_key = f"team_exists:{team_id}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result is not None:
            return cached_result

        team = await self.get_by_id(team_id)
        result = bool(team)
        await self.redis_client.set(cache_key, result, expire=300)
        return result

    async def get_teams_by_id(self, team_ids):
        cache_key = f"teams_by_id:{','.join(map(str, team_ids))}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        pipeline = [{"$match": {"_id": {"$in": team_ids}}}]
        teams = await self.collection.aggregate(pipeline).to_list(length=None)
        await self.redis_client.set(cache_key, teams, expire=300)
        return teams

    async def get_all_teams(self, cursor: Optional[str] = None, limit: int = 20):
        cache_key = f"all_teams:{cursor}:{limit}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        teams_cursor = (
            self.collection.find(query, {"_id": 1, "team_name": 1})
            .sort("_id", 1)
            .limit(limit + 1)
        )
        teams = await teams_cursor.to_list(length=None)

        has_more = len(teams) > limit
        if has_more:
            teams = teams[:limit]

        result = {
            "teams": [
                {"id": str(team["_id"]), "name": team["team_name"]} for team in teams
            ],
            "has_more": has_more,
            "next_cursor": str(teams[-1]["_id"]) if has_more else None,
        }

        await self.redis_client.set(cache_key, result, expire=300)
        return result

    async def get_all_teams_by_province(
        self, province: str, cursor: Optional[str] = None, limit: int = 20
    ):
        cache_key = f"teams_by_province:{province}:{cursor}:{limit}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        query = {"province": province}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        teams_cursor = (
            self.collection.find(query, {"_id": 1, "team_name": 1})
            .sort("_id", 1)
            .limit(limit + 1)
        )
        teams = await teams_cursor.to_list(length=None)

        has_more = len(teams) > limit
        if has_more:
            teams = teams[:limit]

        result = {
            "teams": [
                {"id": str(team["_id"]), "name": team["team_name"]} for team in teams
            ],
            "has_more": has_more,
            "next_cursor": str(teams[-1]["_id"]) if has_more else None,
        }

        await self.redis_client.set(cache_key, result, expire=300)
        return result

    async def get_team_coaches(self, team_ids: List[str]):
        cache_key = f"team_coaches:{','.join(team_ids)}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)  # Deserialize the cached data

        pipeline = [
            {"$match": {"_id": {"$in": [ObjectId(tid) for tid in team_ids]}}},
            {"$unwind": "$team_coaches"},
            {"$group": {"_id": None, "coach_ids": {"$addToSet": "$team_coaches"}}},
            {
                "$lookup": {
                    "from": "Auth",
                    "localField": "coach_ids",
                    "foreignField": "_id",
                    "as": "coach_details",
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "team_coaches": {
                        "$map": {
                            "input": "$coach_details",
                            "as": "coach",
                            "in": {
                                "_id": {"$toString": "$$coach._id"},
                                "name": "$$coach.name",
                            },
                        }
                    },
                }
            },
        ]

        try:
            result = await self.collection.aggregate(pipeline).to_list(length=None)

            if result and isinstance(result, list) and len(result) > 0:
                if "team_coaches" in result[0]:
                    coaches = result[0]["team_coaches"]
                else:
                    return []
            else:
                return []

            # Serialize coaches to JSON string
            coaches_json = json.dumps(coaches)

            # Cache the serialized data
            await self.redis_client.set(cache_key, coaches_json, expire=300)

            return coaches
        except Exception as e:
            logging.exception(f"An error occurred while fetching coaches: {str(e)}")
            return []

    async def get_all_coaches_by_province(
        self, province: str, cursor: Optional[str] = None, limit: int = 20
    ):
        cache_key = f"coaches_by_province:{province}:{cursor}:{limit}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        query = {"role": UserRole.COACH.value, "province": province}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        coaches_cursor = (
            self.auth_collection.find(query, {"_id": 1, "name": 1})
            .sort("_id", 1)
            .limit(limit + 1)
        )
        coaches = await coaches_cursor.to_list(length=None)

        has_more = len(coaches) > limit
        if has_more:
            coaches = coaches[:limit]

        result = {
            "coaches": [
                {"id": str(coach["_id"]), "name": coach["name"]} for coach in coaches
            ],
            "has_more": has_more,
            "next_cursor": str(coaches[-1]["_id"]) if has_more else None,
        }

        await self.redis_client.set(cache_key, result, expire=300)
        return result

    async def remove_user_from_teams(self, user_id, team_ids, session):
        team_object_ids = [ObjectId(team_id) for team_id in team_ids]
        try:
            result = await self.collection.update_many(
                {"_id": {"$in": team_object_ids}},
                {"$pull": {"team_players": user_id}},
                session=session,
            )
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No matching teams found or user not in teams",
                )
            cache_keys = [f"team_users:{tid}" for tid in team_ids] + [
                f"teams_by_id:{','.join(map(str, team_ids))}",
                "all_teams",
                f"team_coaches:{','.join(map(str, team_ids))}",
            ]
            invalidate_caches.delay(team_ids)
            return {"modified_count": result.modified_count}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    async def get_unique_provinces(self):
        return await self.collection.distinct("province")
