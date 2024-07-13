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
from ..routers.BaseRouter import BaseRouter, get_base_router

ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: CreateUserSchema, base_router: BaseRouter = Depends(get_base_router)
):
    return await base_router.auth_controller.register_user(payload)


@router.post("/push_token", status_code=status.HTTP_201_CREATED)
async def get_push_token(
    payload: PushTokenSchema,
    user_id: str = Depends(oauth2.require_user),
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.auth_controller.get_push_token(payload, user_id)


@router.post("/login", response_model=UserResponseSchema)
async def login(
    payload: LoginUserSchema,
    Authorize: AuthJWT = Depends(),
    base_router: BaseRouter = Depends(get_base_router),
    response: Response = None,
):
    return await base_router.auth_controller.login_user(
        payload, Authorize, response=response
    )


@router.post("/checkToken")
async def access_protected_resource(
    Authorize: AuthJWT = Depends(), base_router: BaseRouter = Depends(get_base_router)
):
    # If the function returns without error, it means the user is authenticated and verified
    return {"message": "You have access to this protected resource"}


@router.get("/refresh_token")
async def refresh_token(
    response: Response,
    Authorize: AuthJWT = Depends(),
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.auth_controller.refresh_access_token(response, Authorize)


@router.get("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    Authorize: AuthJWT = Depends(),
    base_router: BaseRouter = Depends(get_base_router),
):
    return base_router.auth_controller.logout(response, Authorize)


@router.get("/delete_user/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    # Authorize: AuthJWT = Depends(),
    user_id: str,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.auth_controller.delete_user(user_id=user_id)  # , Authorize
