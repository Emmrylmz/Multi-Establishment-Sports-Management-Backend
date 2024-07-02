from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi import Depends
from ..database import get_collection
from .MongoDBService import MongoDBService
from .BaseService import BaseService
from ..utils import ensure_object_id
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status


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
        return players

    async def check_team_exists(self, team_id):
        team_id = ensure_object_id(team_id)
        team = await self.get_by_id(team_id)
        return bool(team)

    async def get_teams_by_id(self, team_ids):
        pipeline = [
            {"$match": {"_id": {"$in": team_ids}}},
            {"$project": {"_id": 1, "team_name": 1}},
        ]
        teams = await self.collection.aggregate(pipeline).to_list(length=None)
        return teams

    async def get_all_teams(self):
        teams = await self.collection.find({}, {"_id": 1})
        return teams
