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
from app import utils
from ..oauth2 import require_user
from typing import List, Dict, Any


class TeamController:
    @staticmethod
    async def register_team(
        team_payload: CreateTeamSchema,
        request: Request,
        user: dict = Depends(require_user),
    ):

        app = request.app
        auth_service.validate_role(user, "Coach")
        team_data = team_payload.dict()
        created_team = await team_service.create(team_data)
        if not created_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_BAD_REQUEST,
                detail="Could not create team",
            )
        # If created_event is a Pydantic model, return its .dict(), otherwise return it directly if it's already a dict
        team_id = created_team["_id"]
        await app.rabbit_client.declare_and_bind_queue(
            queue_name=f"{team_id}",
            routing_keys=[f"team.{team_id}.event.*"],
        )
        return created_team

    async def add_user_to_team(team_ids, user_ids):
        user_ids = [utils.ensure_object_id(user_id) for user_id in user_ids]
        team_ids = [utils.ensure_object_id(team_id) for team_id in team_ids]

        role = await auth_service.check_role(user_id=user_ids[0])
        user_role_field = "team_players" if role == "Player" else "team_coaches"

        user_response = await team_service.add_users_to_teams(
            team_ids=team_ids, user_ids=user_ids, user_role_field=user_role_field
        )
        team_response = await auth_service.add_teams_to_users(
            team_ids=team_ids, user_ids=user_ids
        )

        return {
            "results of player/user insertion": {
                str(user_response),
            }
        }

    async def get_team_users_by_id(team_id: str):
        team_id = utils.ensure_object_id(team_id)
        players = await team_service.team_users_list(team_id)
        return players
