from fastapi.responses import JSONResponse
from fastapi import Depends
from dataclasses import asdict
from ..service.AuthService import AuthService
from ..service.TokenService import PushTokenService
from ..service.TeamService import TeamService
from ..service.EventService import EventService
from ..service.UserService import UserService
from ..oauth2 import require_user
from ..utils import hash_password, verify_password, ensure_object_id
from ..dependencies.service_dependencies import (
    get_auth_service,
    get_push_token_service,
    get_team_service,
    get_event_service,
    get_user_service,
)


class BaseController:
    def __init__(
        self,
        user_service: UserService = Depends(get_user_service),
        token_service: PushTokenService = Depends(get_push_token_service),
        team_service: TeamService = Depends(get_team_service),
        event_service: EventService = Depends(get_event_service),
        auth_service: AuthService = Depends(get_auth_service),
    ):
        self.user_service = user_service
        self.token_service = token_service
        self.team_service = team_service
        self.event_service = event_service
        self.auth_service = auth_service
        self.hash_handler = hash_password
        self.verify_hash = verify_password
        self.format_handler = ensure_object_id
        self.require_user = require_user

    # def _create_response(
    #     self, message: str, success: bool, data: dict = None
    # ) -> JSONResponse:
    #     response = dto.ResponseMessage(message=message, success=success, data=data)
    #     return JSONResponse(content=asdict(response))
