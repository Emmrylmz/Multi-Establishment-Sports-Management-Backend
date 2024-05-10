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
        print('register_team start')
        app = request.app
        user_service.validate_role(user, "Coach")
        team_data = team_payload.dict()
        created_team = await team_service.create(team_data)
        if not created_team:
<<<<<<< HEAD
            raise HTTPException(
                status_code=status.HTTP_400_BAD_BAD_REQUEST,
                detail="Could not create team",
            )
        # If created_event is a Pydantic model, return its .dict(), otherwise return it directly if it's already a dict
        await app.rabbit_client.start_subscription(
            queue_name=str(created_team["team_name"])
        )
=======
            raise HTTPException(status_code=400, detail="Could not create team")
        
        print('created_team', created_team)

        # Set up a queue for the new team
        team_id = created_team['team_id']
        await request.app.rabbit_client.declare_and_bind_queue(
            queue_name=f"team_{team_id}_events",
            routing_keys=[f"team.{team_id}.event.*"]
        )
        
        print('queue set up')

>>>>>>> rabbit_stann
        return created_team
    
    @staticmethod
    async def add_new_player(
        team_id: str, player_name: str,
        request: Request,
        user: dict = Depends(require_user),
    ):
        print('register_team start')
        app = request.app
        UserService.validate_role(user, "Coach")

        updated_team = await team_service.add_player_to_team(team_id, player_name)

        # Set up a queue for the new team
        team_id = updated_team['team_id']
        await request.app.rabbit_client.publish_message(
            routing_key=f"team.{team_id}.event.updated",
            message={
                "event": updated_team.dict(),  # Convert the Pydantic model to a dictionary here
                "action": "updated"
            }
        )
        
        print('queue set up')

        return updated_team

    async def add_user_to_team(team_id, user_id):
        response = await team_service.insert_user(team_id=team_id, user_id=user_id)
        return response
