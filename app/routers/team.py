from fastapi import APIRouter, status, Depends, HTTPException, Request
from typing import List
from ..oauth2 import require_user
from ..service.EventService import EventService
from bson import ObjectId
from ..models.team_schemas import CreateTeamSchema
from ..controller.TeamController import TeamController

router = APIRouter()


@router.post("/create", response_model=CreateTeamSchema)
async def create_team(
    team: CreateTeamSchema, request: Request, user: dict = Depends(require_user)
):
    return await TeamController.register_team(team, request, user)
