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
from ..service.TeamService import team_service
from ..service.UserService import user_service


class TeamController:
    @staticmethod
    async def register_team(
        team_payload: CreateTeamSchema,
        request: Request,
        user: dict = Depends(require_user),
    ):

        app = request.app
        user_service.validate_role(user, "Coach")
        team_data = team_payload.dict()
        created_team = await team_service.create(team_data)
        if not created_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_BAD_REQUEST,
                detail="Could not create team",
            )
        # If created_event is a Pydantic model, return its .dict(), otherwise return it directly if it's already a dict
        await app.rabbit_client.start_subscription(
            queue_name=str(created_team["team_name"])
        )
        return created_team
