from fastapi import APIRouter, Depends, Request
from typing import List
from ..oauth2 import require_user
from ..models.team_schemas import CreateTeamSchema, PlayerTokenRequest
from ..controller.TeamController import TeamController
from ..service.TokenService import push_token_service
from ..service.TeamService import team_service

router = APIRouter()


@router.post("/create", response_model=CreateTeamSchema)
async def create_team(
    team: CreateTeamSchema, request: Request, user: dict = Depends(require_user)
):
    return await TeamController.register_team(team, request, user)


# @router.get("/get/{team_id}", response_model=CreateTeamSchema)
# async def create_team():
#     return await team_service.get_by_id(team_id)


@router.post("/get_token")  # Assuming it returns a list of tokens
async def get_tokens(request: PlayerTokenRequest):
    return await push_token_service.get_team_player_tokens(team_id=request.team_id)
