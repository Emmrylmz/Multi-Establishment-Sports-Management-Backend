from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Dict, Any, Optional
import logging
import json
from app.database import get_collection


class TeamRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = None  # Assuming the collection name is 'Team'
        self.auth_collection = None  # Assuming the collection name is 'Auth'

    @classmethod
    async def initialize(cls, database: AsyncIOMotorDatabase):
        self = cls(database)
        self.collection = await get_collection("Team", database)
        self.auth_collection = await get_collection("Auth", database)
        return self

    async def add_user_to_teams(
        self, user_id: ObjectId, team_ids: List[str], user_role_field: str, session=None
    ):
        result = await self.collection.update_many(
            {"_id": {"$in": [ObjectId(tid) for tid in team_ids]}},
            {"$addToSet": {user_role_field: user_id}},
            session=session,
        )
        return result

    async def get_team_users_by_id(self, team_id: str) -> List[Dict[str, Any]]:
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
        return results

    async def get_teams_by_id(self, team_ids: List[ObjectId]) -> List[Dict[str, Any]]:
        pipeline = [{"$match": {"_id": {"$in": team_ids}}}]
        teams = await self.collection.aggregate(pipeline).to_list(length=None)
        return teams

    async def get_all_teams(
        self, cursor: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        query = {}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}
        teams_cursor = (
            self.collection.find(query, {"_id": 1, "team_name": 1})
            .sort("_id", 1)
            .limit(limit + 1)
        )
        teams = await teams_cursor.to_list(length=None)
        return teams

    async def get_all_teams_by_province(
        self, province: str, cursor: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        query = {"province": province}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}
        teams_cursor = (
            self.collection.find(query, {"_id": 1, "team_name": 1})
            .sort("_id", 1)
            .limit(limit + 1)
        )
        teams = await teams_cursor.to_list(length=None)
        return teams

    async def get_team_coaches(self, team_ids: List[ObjectId]) -> List[Dict[str, Any]]:
        pipeline = [
            {"$match": {"_id": {"$in": team_ids}}},
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
        result = await self.collection.aggregate(pipeline).to_list(length=None)
        return result

    async def get_all_coaches_by_province(
        self, province: str, cursor: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        query = {"role": "COACH", "province": province}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}
        coaches_cursor = (
            self.auth_collection.find(query, {"_id": 1, "name": 1})
            .sort("_id", 1)
            .limit(limit + 1)
        )
        coaches = await coaches_cursor.to_list(length=None)
        return coaches

    async def remove_user_from_teams(
        self, user_id: ObjectId, team_ids: List[ObjectId], session=None
    ):
        result = await self.collection.update_many(
            {"_id": {"$in": team_ids}},
            {"$pull": {"team_players": user_id}},
            session=session,
        )
        return result

    async def get_unique_provinces(self) -> List[str]:
        provinces = await self.collection.distinct("province")
        return provinces

    async def get_all_team_ids_by_province(
        self, province: str, session=None
    ) -> List[str]:
        teams = await self.collection.find(
            {"province": province}, {"_id": 1}, session=session
        ).to_list(None)
        return [str(team["_id"]) for team in teams]
