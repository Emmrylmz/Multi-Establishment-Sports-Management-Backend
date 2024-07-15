from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi import Depends
from ..database import get_collection
from .MongoDBService import MongoDBService
from .BaseService import BaseService
from ..utils import ensure_object_id
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status
from bson import ObjectId
from typing import List


class TeamService(MongoDBService):
    def __init__(
        self,
        collection: AsyncIOMotorCollection = Depends(lambda: get_collection("Team")),
        # auth_collection: AsyncIOMotorCollection = Depends(
        #     lambda: get_collection("Auth")
        # ),
    ):
        self.collection = collection
        self.auth_collection = get_collection("Auth")

        super().__init__(self.collection)

    async def add_users_to_teams(
        self, user_ids, team_ids, user_role_field, register=True
    ):
        try:
            client = self.collection.database.client

            async with await client.start_session() as session:
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

    async def team_users_list(self, team_id: str):
        team = await self.get_by_id(team_id)
        players = team["team_players"]
        coaches = team["team_coaches"]
        return players, coaches

    async def check_team_exists(self, team_id):
        team_id = ensure_object_id(team_id)
        team = await self.get_by_id(team_id)
        return bool(team)

    async def get_teams_by_id(self, team_ids):
        pipeline = [{"$match": {"_id": {"$in": team_ids}}}]
        teams = await self.collection.aggregate(pipeline).to_list(length=None)
        return teams

    async def get_all_teams(self):
        teams_cursor = self.collection.find({}, {"_id": 1})
        teams = await teams_cursor.to_list(length=None)
        return [team["_id"] for team in teams]

    async def get_all_teams_by_province(self, province):
        teams_cursor = self.collection.find({"province": province}, {"_id": 1})
        teams = await teams_cursor.to_list(length=None)
        return [team["_id"] for team in teams]

    async def remove_user_from_teams(self, user_id, team_ids):
        team_object_ids = [ObjectId(team_id) for team_id in team_ids]
        try:
            result = await self.collection.update_many(
                {"_id": {"$in": team_object_ids}}, {"$pull": {"team_players": user_id}}
            )
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No matching teams found or user not in teams",
                )

            return {"modified_count": result.modified_count}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    async def get_team_coaches(self, team_ids: List[str]):
        pipeline = [
            {"$match": {"_id": {"$in": team_ids}}},
            {"$unwind": "$team_coaches"},
            {"$group": {"_id": None, "coach_ids": {"$addToSet": "$team_coaches"}}},
            {
                "$lookup": {
                    "from": "Auth",
                    # this will come from User_Info
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
                            "in": {"_id": "$$coach._id", "name": "$$coach.name"},
                        }
                    },
                }
            },
        ]

        result = await self.collection.aggregate(pipeline).to_list(length=None)

        return result

    async def get_all_coaches_by_province(self, province: str):
        cursor = self.auth_collection.find(
            {"role": "Coach", "province": province}, projection={"_id": 1, "name": 1}
        )
        result = await cursor.to_list(length=None)
        return result
