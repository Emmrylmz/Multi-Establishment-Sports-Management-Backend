import base64
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from bson.objectid import ObjectId
from fastapi_jwt_auth.exceptions import AuthJWTException
from app.service.UserService import UserService, user_service


from app.serializers.userSerializer import userEntity

from .database import User
from .config import settings


class Settings(BaseModel):
    authjwt_algorithm: str = settings.ALGORITHM
    authjwt_decode_algorithms: List[str] = [settings.ALGORITHM]
    authjwt_token_location: set = {"cookies", "headers"}
    authjwt_access_cookie_key: str = "access_token"
    authjwt_refresh_cookie_key: str = "refresh_token"
    authjwt_cookie_csrf_protect: bool = False
    authjwt_public_key: str = settings.JWT_PUBLIC_KEY
    authjwt_private_key: str = settings.JWT_PRIVATE_KEY


@AuthJWT.load_config
def get_config():
    config = Settings()
    config.authjwt_public_key = base64.b64decode(config.authjwt_public_key).decode(
        "utf-8"
    )
    config.authjwt_private_key = base64.b64decode(config.authjwt_private_key).decode(
        "utf-8"
    )
    return config


class NotVerified(Exception):
    pass


class UserNotFound(Exception):
    pass


async def require_user(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
        user_id = Authorize.get_jwt_subject()
        user = await user_service.get_by_id(user_id)

        if not user:
            raise UserNotFound("User no longer exists")

    except AuthJWTException as e:
        # Handle errors from AuthJWT specifically
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication problem: Token is invalid or expired",
        )
    except UserNotFound as e:
        # Specific error for user not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotVerified as e:
        # Specific error for unverified users
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return user
