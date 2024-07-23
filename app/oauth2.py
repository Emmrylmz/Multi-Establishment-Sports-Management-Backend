import base64
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseSettings
from .config import settings
from fastapi import Depends, HTTPException, status


class AuthSettings(BaseSettings):
    authjwt_algorithm: str = settings.ALGORITHM
    authjwt_decode_algorithms: list = [settings.ALGORITHM]
    authjwt_token_location: set = {"cookies", "headers"}
    authjwt_access_cookie_key: str = "access_token"
    authjwt_refresh_cookie_key: str = "refresh_token"
    authjwt_cookie_csrf_protect: bool = False
    authjwt_private_key: str = settings.JWT_PRIVATE_KEY
    authjwt_public_key: str = settings.JWT_PUBLIC_KEY
    # authjwt_private_key: str = base64.b64decode(settings.JWT_PRIVATE_KEY).decode(
    #     "UTF-8"
    # )
    # authjwt_public_key: str = base64.b64decode(settings.JWT_PUBLIC_KEY).decode("UTF-8")
    # YAML FILES AUTOMATICALLY B64 decode themselves


@AuthJWT.load_config
def get_config():
    return AuthSettings()


class NotVerified(Exception):
    pass


class UserNotFound(Exception):
    pass


async def require_user(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
        user_id = Authorize.get_jwt_subject()

        if not user_id:
            raise UserNotFound("User no longer exists")

    except AuthJWTException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication problem: Token is invalid or expired",
        )
    except UserNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotVerified as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return user_id
