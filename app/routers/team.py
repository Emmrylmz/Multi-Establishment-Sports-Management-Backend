from fastapi import APIRouter, Depends, Request
from ..oauth2 import require_user
from ..models.team_schemas import (
    CreateTeamSchema,
    PlayerTokenRequest,
    UserInsert,
    TeamPlayers,
)
from ..controller.TeamController import TeamController
from .BaseRouter import BaseRouter


class TeamRouter(BaseRouter):
    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter()
        self._init_routes()

    def _init_routes(self) -> None:
        @self.router.post("/create", response_model=CreateTeamSchema)
        async def create_team(
            team: CreateTeamSchema, request: Request, user: dict = Depends(require_user)
        ):
            return await TeamController.register_team(team, request, user)

        # NEEDS ADJUSTMENTS NO SERVICE USE ON ROUTER USE ON CONTROLLER INSTEAD
        @self.router.post("/get_token")
        async def get_tokens(request: PlayerTokenRequest):
            return await push_token_service.get_team_player_tokens(
                team_id=request.team_id
            )

        @self.router.post("/insert_users_and_teams")
        async def insert_user(request: UserInsert):
            return await TeamController.add_user_to_team(
                team_ids=request.team_ids, user_ids=request.user_ids
            )

        @self.router.post("/get_team_users")
        async def get_team_users(request: TeamPlayers):
            return await TeamController.get_team_users_by_id(request.team_id)


team_router = TeamRouter().router
