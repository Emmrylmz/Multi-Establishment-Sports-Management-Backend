from fastapi import (
    HTTPException,
    status,
    APIRouter,
    Response,
    status,
    Depends,
    HTTPException,
    Request,
)
from ..models.team_schemas import CreateTeamSchema
from datetime import datetime, timedelta
from app.config import settings
from typing import List, Dict, Any, Set
from ..service import TeamService, AuthService, UserService


class TeamController:
    @classmethod
    async def create(
        cls,
        team_service: TeamService,
        auth_service: AuthService,
        user_service: UserService,
    ):
        self = cls.__new__(cls)
        await self.__init__(team_service, auth_service, user_service)
        return self

    def __init__(
        self,
        team_service: TeamService,
        auth_service: AuthService,
        user_service: UserService,
    ):
        self.team_service = team_service
        self.auth_service = auth_service
        self.user_service = user_service

    async def register_team(
        self,
        team_payload: CreateTeamSchema,
        request: Request,
        user_id: dict,
    ):
        app = request.app
        user = await self.auth_service.validate_role(user_id, "Coach")
        team_data = team_payload.dict()

        # Create the team
        created_team = await self.team_service.create(team_data)
        if not created_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create team",
            )

        team_id = created_team["_id"]

        # Declare and bind queue
        await app.rabbit_client.create_team_queue(str(team_id))

        # Get the province of the created team
        province = team_data.get("province")

        # Fetch all managers in the same province
        managers_cursor = await self.auth_service.get_users_by_role_and_province(
            "Manager", province
        )
        managers = await managers_cursor.to_list(length=None)

        # Update each manager's team_ids array
        for manager in managers:
            if team_id not in manager.get("teams", []):
                manager["teams"].append(team_id)
                await self.auth_service.update_user_team_ids(
                    manager["_id"], manager["teams"]
                )

        return created_team

    async def add_user_to_team(self, team_ids, user_ids):
        user_ids = [self.format_handler(user_id) for user_id in user_ids]
        team_ids = [self.format_handler(team_id) for team_id in team_ids]
        role = await self.auth_service.check_role(user_id=user_ids[0])
        user_role_field = "team_players" if role == "Player" else "team_coaches"
        user_response = await self.team_service.add_users_to_teams(
            team_ids=team_ids,
            user_ids=user_ids,
            user_role_field=user_role_field,
            register=False,
        )
        return {
            "results of player/user insertion": {
                str(user_response),
            }
        }

    async def get_team_users_by_id(self, team_id: str):
        team_id = self.format_handler(team_id)
        return await self.team_service.get_team_users_by_id(team_id)

    async def get_teams_by_id(self, team_ids: List[str]):
        object_ids = [self.format_handler(team_id) for team_id in team_ids]
        teams = await self.team_service.get_teams_by_id(object_ids)
        return teams

    async def get_team_coaches(self, team_ids: List[str]):
        try:
            # Convert team_ids to ObjectId
            team_object_ids = [self.format_handler(team_id) for team_id in team_ids]

            # Aggregation pipeline to fetch teams and their coaches
            result = await self.team_service.get_team_coaches(team_object_ids)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No coaches found for the given teams",
                )

            coaches = result[0]["team_coaches"]
            return coaches

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while fetching coaches: {str(e)}",
            )

    async def get_all_coaches(self, province: str):
        return await self.team_service.get_all_coaches_by_province(province)
