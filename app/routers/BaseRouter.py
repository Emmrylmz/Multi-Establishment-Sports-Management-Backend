from ..controller.AuthController import AuthController
from ..controller.UserController import UserController
from ..controller.EventController import EventController
from ..controller.TeamController import TeamController
from ..controller.PaymentController import PaymentController
from ..controller.ConstantsController import ConstantsController
from ..controller.NoteController import NoteController
from fastapi import Depends
from ..oauth2 import require_user
from ..service.AuthService import AuthService
from ..service.UserService import UserService
from ..service.TokenService import PushTokenService
from ..service.TeamService import TeamService
from ..service.PaymentService import PaymentService
from ..service.EventService import EventService
from ..service.ConstantsService import ConstantsService
from ..service.NoteService import NoteService
from ..dependencies.service_dependencies import (
    get_auth_service,
    get_user_service,
    get_push_token_service,
    get_team_service,
    get_event_service,
    get_payment_service,
    get_constants_service,
    get_note_service,
)


class BaseRouter:
    def __init__(
        self,
        auth_service: AuthService = Depends(get_auth_service),
        user_service: UserService = Depends(get_user_service),
        token_service: PushTokenService = Depends(get_push_token_service),
        team_service: TeamService = Depends(get_team_service),
        event_service: EventService = Depends(get_event_service),
        payment_service: PaymentService = Depends(get_payment_service),
        constants_service: ConstantsService = Depends(get_constants_service),
        note_service: NoteService = Depends(get_note_service),
    ) -> None:
        self.auth_controller = AuthController(auth_service, token_service, team_service)
        self.user_controller = UserController(user_service)
        self.team_controller = TeamController(team_service, auth_service, user_service)
        self.event_controller = EventController(
            event_service, auth_service, payment_service
        )
        self.payment_controller = PaymentController(payment_service, user_service)
        self.constants_controller = ConstantsController(constants_service)
        self.note_controller = NoteController(auth_service, note_service)

    def get_current_user(self, user: dict = Depends(require_user)):
        return user


# dependencies.py (or in auth_router.py if you prefer to keep it together)
def get_base_router(
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
    token_service: PushTokenService = Depends(get_push_token_service),
    team_service: TeamService = Depends(get_team_service),
    event_service: EventService = Depends(get_event_service),
    payment_service: PaymentService = Depends(get_payment_service),
    constants_service: ConstantsService = Depends(get_constants_service),
    note_service: NoteService = Depends(get_note_service),
) -> BaseRouter:
    return BaseRouter(
        auth_service=auth_service,
        user_service=user_service,
        token_service=token_service,
        team_service=team_service,
        event_service=event_service,
        payment_service=payment_service,
        constants_service=constants_service,
        note_service=note_service,
    )
