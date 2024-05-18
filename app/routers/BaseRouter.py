from ..controller.AuthController import AuthController
from ..controller.UserController import UserController
from ..controller.EventController import EventController
from ..controller.TeamController import TeamController
from fastapi import Depends
from ..oauth2 import require_user


class BaseRouter:
    auth_controller: AuthController
    user_controller: UserController
    team_controller: TeamController
    event_controller: EventController

    def __init__(self) -> None:
        self.auth_controller = AuthController()
        self.user_controller = UserController()
        self.team_controller = TeamController()
        self.event_controller = EventController()

    def get_current_user(self, user: dict = Depends(require_user)):
        return user
