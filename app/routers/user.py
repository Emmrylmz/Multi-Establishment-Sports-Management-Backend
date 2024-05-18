from fastapi import APIRouter, Depends, Request
from ..oauth2 import require_user
from ..models.user_schemas import UserAttributesSchema
from ..controller.UserController import UserController
from .BaseRouter import BaseRouter


class UserRouter(BaseRouter):
    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter()
        self._init_routes()

    def _init_routes(self) -> None:
        @self.router.post("/update")
        async def create_team(
            payload: UserAttributesSchema, user: dict = Depends(self.get_current_user)
        ):
            return await self.user_controller.update_user_information(payload, user)


user_router = UserRouter().router
