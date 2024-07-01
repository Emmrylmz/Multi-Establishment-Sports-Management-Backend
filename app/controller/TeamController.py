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
from typing import List, Dict, Any
from .BaseController import BaseController
from ..service import TeamService, AuthService, UserService


class TeamController(BaseController):
    def __init__(
        self,
        team_service: TeamService,
        auth_service: AuthService,
        user_service: UserService,
    ):
        super().__init__()  # Initialize the BaseController
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
        created_team = await self.team_service.create(team_data)
        if not created_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create team",
            )
        team_id = created_team["_id"]
        await app.rabbit_client.declare_and_bind_queue(
            queue_name=f"{team_id}",
            routing_keys=[f"team.{team_id}.event.*"],
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
        players = await self.team_service.team_users_list(team_id)

        # Convert player IDs to ObjectId if they are in string format
        player_ids = [self.format_handler(player_id) for player_id in players]

        # Query all users at once using the $in operator
        user_infos = await self.user_service.get_users_by_id(player_ids)

        return user_infos

    async def get_teams_by_id(self, team_ids: List[str]):
        object_ids = [self.format_handler(team_id) for team_id in team_ids]
        teams = await self.team_service.get_teams_by_id(object_ids)
        return teams
