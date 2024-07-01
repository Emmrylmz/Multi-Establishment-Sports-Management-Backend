from fastapi import APIRouter, Depends, Request, status
from ..models.team_schemas import (
    CreateTeamSchema,
    UserInsert,
    TeamPlayers,
    TeamQueryById,
)
from ..oauth2 import require_user
from .BaseRouter import BaseRouter, get_base_router

router = APIRouter()


@router.post(
    "/create", response_model=CreateTeamSchema, status_code=status.HTTP_201_CREATED
)
async def create_team(
    team: CreateTeamSchema,
    request: Request,
    user_id: dict = Depends(require_user),
    base_router: BaseRouter = Depends(get_base_router),
):
    """
    Create a new team.
    """
    return await base_router.team_controller.register_team(team, request, user_id)


@router.post("/insert_users_to_teams", status_code=status.HTTP_201_CREATED)
async def insert_user(
    request: UserInsert,
    base_router: BaseRouter = Depends(get_base_router),
):
    """
    Insert users into teams.
    """
    return await base_router.team_controller.add_user_to_team(
        team_ids=request.team_ids, user_ids=request.user_ids
    )


@router.post("/get_team_users", status_code=status.HTTP_200_OK)
async def get_team_users(
    request: TeamPlayers,
    base_router: BaseRouter = Depends(get_base_router),
):
    """
    Get users of a team by team ID.
    """
    return await base_router.team_controller.get_team_users_by_id(
        team_id=request.team_id
    )


@router.post("/get_team_by_id", status_code=status.HTTP_200_OK)
async def get_team_by_id(
    request: TeamQueryById,
    base_router: BaseRouter = Depends(get_base_router),
):
    """
    Get team details by team IDs.
    """
    return await base_router.team_controller.get_teams_by_id(team_ids=request.team_ids)
