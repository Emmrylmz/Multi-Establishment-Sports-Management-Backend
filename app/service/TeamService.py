from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from ..database import Team
from pymongo.errors import PyMongoError
from fastapi import HTTPException, status
from ..utils import ensure_object_id
from .BaseService import BaseService


class TeamService(BaseService):
    def __init__(self):
        super().__init__(Team)

    # def entity(self, document: dict):
    #     # Customize how event documents are transformed before they are returned
    #     if document:
    #         document["start_date"] = document["start_date"].strftime(
    #             "%Y-%m-%d %H:%M:%S"
    #         )
    #     return super().entity(document)

    # Add event-specific methods if necessary
    def get_upcoming_events(self):
        return self.list({"start_date": {"$gte": datetime.utcnow()}})

    async def add_users_to_teams(
        self, user_ids, team_ids, user_role_field, register=True
    ):

        try:
            # Get the client from one of the collections
            client = self.collection.database.client

            async with await client.start_session() as session:
                async with session.start_transaction():
                    # Add users to teams
                    teams_update_result = await self.collection.update_many(
                        {"_id": {"$in": team_ids}},
                        {"$addToSet": {user_role_field: {"$each": user_ids}}},
                        session=session,
                    )
                    print(teams_update_result)

                    # Initialize users_update_result for consistent return structure
                    users_update_result = None

                    # Conditionally add teams to users
                    if not register:
                        users_update_result = await self.auth_collection.update_many(
                            {"_id": {"$in": user_ids}},
                            {"$addToSet": {"teams": {"$each": team_ids}}},
                            session=session,
                        )

                    # Check results based on the value of register
                    if teams_update_result.modified_count > 0 and (
                        register
                        or (not register and users_update_result.modified_count > 0)
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
        if team:
            return True
        else:
            return False

    async def get_teams_by_id(self, team_ids):
        pipeline = [
            {"$match": {"_id": {"$in": team_ids}}},
            {"$project": {"_id": 1, "team_name": 1}},
        ]

        teams = await self.collection.aggregate(pipeline).to_list(length=None)
        return teams
