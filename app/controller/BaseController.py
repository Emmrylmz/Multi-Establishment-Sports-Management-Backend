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


class BaseController:
    def __init__(self) -> None:
        self.user_service = UserService()
        self.token_service = PushTokenService()
        self.team_service = TeamService()
        self.event_service = EventService()
        self.auth_service = AuthService()
        self.hash_handler = hash_password
        self.verify_hash = verify_password
        self.format_handler = ensure_object_id
        self.require_user = require_user

    # def _create_response(
    #     self, message: str, success: bool, data: dict = None
    # ) -> JSONResponse:
    #     response = dto.ResponseMessage(message=message, success=success, data=data)
    #     return JSONResponse(content=asdict(response))
