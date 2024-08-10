from fastapi import APIRouter, Depends, Request, status
from ..models.team_schemas import (
    CreateTeamSchema,
    UserInsert,
    TeamPlayers,
    TeamQueryById,
    TeamCoachesQuery,
)
from ..oauth2 import require_user
from typing import List
from ..controller.TeamController import TeamController
from ..dependencies.controller_dependencies import get_team_controller

router = APIRouter()


@router.post(
    "/create", response_model=CreateTeamSchema, status_code=status.HTTP_201_CREATED
)
async def create_team(
    team: CreateTeamSchema,
    request: Request,
    user_id: dict = Depends(require_user),
    team_controller: TeamController = Depends(get_team_controller),
):
    """
    Create a new team.
    """
    return await team_controller.register_team(team, request, user_id)


@router.post("/insert_user_to_teams", status_code=status.HTTP_201_CREATED)
async def insert_user(
    request: UserInsert, team_controller: TeamController = Depends(get_team_controller)
):
    """
    Insert users into teams.
    """
    return await team_controller.add_user_to_teams(
        team_ids=request.team_ids, user_id=request.user_id
    )


@router.post("/get_team_users", status_code=status.HTTP_200_OK)
async def get_team_users(
    payload: TeamPlayers, team_controller: TeamController = Depends(get_team_controller)
):
    """
    Get users of a team by team ID.
    """
    return await team_controller.get_team_users_by_id(team_id=payload.team_id)


@router.post("/get_team_by_id", status_code=status.HTTP_200_OK)
async def get_team_by_id(
    request: TeamQueryById,
    team_controller: TeamController = Depends(get_team_controller),
):
    """
    Get team details by team IDs.
    """
    return await team_controller.get_teams_by_id(team_ids=request.team_ids)


@router.post("/get_team_coaches", status_code=status.HTTP_200_OK)
async def get_team_coaches(
    payload: TeamCoachesQuery,
    team_controller: TeamController = Depends(get_team_controller),
):
    return await team_controller.get_team_coaches(team_ids=payload.team_ids)


@router.get("/get_all_coaches_by_province/{province}", status_code=status.HTTP_200_OK)
async def get_all_coaches(
    team_controller: TeamController = Depends(get_team_controller),
    province: str = None,
):
    return await team_controller.get_all_coaches(province=province)
