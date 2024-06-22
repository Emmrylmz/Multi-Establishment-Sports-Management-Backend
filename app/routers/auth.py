from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fastapi import Response, status, Depends, HTTPException, APIRouter
from app import oauth2
from .. import utils
from ..models.user_schemas import (
    LoginUserSchema,
    CreateUserSchema,
    UserAttributesSchema,
    UserResponseSchema,
)
from app.oauth2 import AuthJWT
from ..config import settings
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT
from ..models.firebase_token_schemas import PushTokenSchema
from .BaseRouter import BaseRouter


ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


class AuthRouter(BaseRouter):
    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter()
        self._init_routes()

    def _init_routes(self) -> None:
        @self.router.post(
            "/register",
            status_code=status.HTTP_201_CREATED,
        )
        async def register(payload: CreateUserSchema):
            return await self.auth_controller.register_user(payload=payload)

        @self.router.post(
            "/push_token",
            status_code=status.HTTP_201_CREATED,
        )
        async def get_push_token(
            payload: PushTokenSchema, user: dict = Depends(self.get_current_user)
        ):
            return await self.auth_controller.get_push_token(payload, user)

        @self.router.post("/login", response_model=UserResponseSchema)
        async def login(payload: LoginUserSchema, Authorize: AuthJWT = Depends()):
            return await self.auth_controller.login_user(payload, Authorize)

        @self.router.post("/checkToken")
        async def access_protected_resource(
            Authorize: AuthJWT = Depends(self.get_current_user),
        ):
            # If the function returns without error, it means the user is authenticated and verified
            return {"message": "You have access to this protected resource"}

        @self.router.get("/refresh_token")
        def refresh_token(response: Response, Authorize: AuthJWT = Depends()):
            return self.auth_controller.refresh_access_token(response, Authorize)

        @self.router.get("/logout", status_code=status.HTTP_200_OK)
        def logout(
            response: Response,
            Authorize: AuthJWT = Depends(),
            user_id: str = Depends(self.get_current_user),
        ):
            return self.auth_controller.logout(response, Authorize, user_id)


auth_router = AuthRouter().router
