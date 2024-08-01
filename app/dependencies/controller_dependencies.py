from fastapi import Depends
from ..service.TokenService import PushTokenService
from ..service.TeamService import TeamService
from ..service.EventService import EventService
from ..service.UserService import UserService
from ..service.AuthService import AuthService
from ..service.PaymentService import PaymentService
from ..service.ConstantsService import ConstantsService
from ..service.NoteService import NoteService
from ..controller.AuthController import AuthController
from ..controller.EventController import EventController
from ..controller.NoteController import NoteController
from ..controller.TeamController import TeamController
from ..controller.PaymentController import PaymentController
from ..controller.ConstantsController import ConstantsController
from ..controller.UserController import UserController

from .service_dependencies import (
    get_event_service,
    get_auth_service,
    get_payment_service,
    get_team_service,
    get_push_token_service,
    get_constants_service,
    get_note_service,
    get_push_token_service,
    get_user_service,
)


# EventController dependency
# EventController dependency
async def get_event_controller(
    event_service: EventService = Depends(get_event_service),
    auth_service: AuthService = Depends(get_auth_service),
    payment_service: PaymentService = Depends(get_payment_service),
    team_service: TeamService = Depends(get_team_service),
) -> EventController:
    return EventController(event_service, auth_service, payment_service, team_service)


# AuthController dependency
async def get_auth_controller(
    auth_service: AuthService = Depends(get_auth_service),
    token_service: PushTokenService = Depends(get_push_token_service),
    team_service: TeamService = Depends(get_team_service),
) -> AuthController:
    return AuthController(auth_service, token_service, team_service)


# ConstantsController dependency
async def get_constants_controller(
    constants_service: ConstantsService = Depends(get_constants_service),
) -> ConstantsController:
    return ConstantsController(constants_service)


# NoteController dependency
async def get_note_controller(
    auth_service: AuthService = Depends(get_auth_service),
    note_service: NoteService = Depends(get_note_service),
) -> NoteController:
    return NoteController(auth_service, note_service)


# PaymentController dependency
async def get_payment_controller(
    payment_service: PaymentService = Depends(get_payment_service),
    user_service: UserService = Depends(get_user_service),
) -> PaymentController:
    return PaymentController(payment_service, user_service)


# TeamController dependency
async def get_team_controller(
    team_service: TeamService = Depends(get_team_service),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> TeamController:
    return TeamController(team_service, auth_service, user_service)


# UserController dependency
async def get_user_controller(
    user_service: UserService = Depends(get_user_service),
) -> UserController:
    return UserController(user_service)
