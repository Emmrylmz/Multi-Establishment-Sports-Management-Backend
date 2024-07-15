from fastapi import APIRouter, Depends, Request, status
from ..models.team_schemas import (
    CreateTeamSchema,
    UserInsert,
    TeamPlayers,
    TeamQueryById,
    TeamCoachesQuery,
)
from ..oauth2 import require_user
from .BaseRouter import BaseRouter, get_base_router
from typing import List

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
    payload: TeamPlayers,
    base_router: BaseRouter = Depends(get_base_router),
):
    """
    Get users of a team by team ID.
    """
    return await base_router.team_controller.get_team_users_by_id(
        team_id=payload.team_id
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


@router.post("/get_team_coaches", status_code=status.HTTP_200_OK)
async def get_team_coaches(
    payload: TeamCoachesQuery,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.team_controller.get_team_coaches(team_ids=payload.team_ids)


@router.get("/get_all_coaches_by_province/{province}", status_code=status.HTTP_200_OK)
async def get_all_coaches(
    base_router: BaseRouter = Depends(get_base_router),
    province: str = None,
):
    return await base_router.team_controller.get_all_coaches(province=province)
