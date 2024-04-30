from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fastapi import APIRouter, Response, status, Depends, HTTPException
from app import oauth2
from app.database import User
from app.serializers.userSerializer import userEntity, userResponseEntity
from .. import utils
from ..models import schemas
from app.oauth2 import AuthJWT, require_user
from ..config import settings
from fastapi import APIRouter
from app.controller.AuthController import AuthController
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from fastapi_jwt_auth import AuthJWT


router = APIRouter()
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.UserResponse,
)
async def register(payload: schemas.CreateUserSchema):
    return AuthController.register_user(payload)


@router.post("/login")
def login(payload: schemas.LoginUserSchema, Authorize: AuthJWT = Depends()):
    return AuthController.login_user(payload, Authorize)


@router.post("/checkToken")
async def access_protected_resource(Authorize: AuthJWT = Depends(require_user)):
    # If the function returns without error, it means the user is authenticated and verified
    return {"message": "You have access to this protected resource"}


@router.get("/refresh")
def refresh_token(response: Response, Authorize: AuthJWT = Depends()):
    return AuthController.refresh_access_token(response, Authorize)


@router.get("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    Authorize: AuthJWT = Depends(),
    user_id: str = Depends(oauth2.require_user),
):
    return AuthController.logout(response, Authorize, user_id)
