# app/controllers/auth_controller.py

from fastapi import HTTPException, status
from app.service.TeamService import TeamService
from app.service.UserService import UserService
from ..models import schemas
from fastapi import APIRouter, Response, status, Depends, HTTPException
from datetime import datetime, timedelta
from app.config import settings
from app import utils
from ..database import Team
from ..database import User

team_service = TeamService(Team)
user_service = UserService(User)


class AuthController:
    @staticmethod
    async def register_user(create_user_schema: schemas.CreateUserSchema):
        if await user_service.check_user_exists(create_user_schema.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
            )

        if create_user_schema.password != create_user_schema.passwordConfirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
            )

        user_data = create_user_schema.dict(exclude_none=False)
        hashed_password = utils.hash_password(user_data["password"])
        user_data["password"] = hashed_password
        user_data.pop("passwordConfirm", None)

        new_user = await user_service.create(user_data)
        print(new_user)
        
        if user_data.get("role") == "Player" and "teams" in user_data:
            for team_id in user_data["teams"]:
                await team_service.add_player_to_team(team_id=team_id, player_name=user_data["name"])
        
        user_dict = {k: v for k, v in new_user.items() if k != "password"}
        return {"status": "success", "user": user_dict}

    @staticmethod
    async def login_user(login_user_schema: schemas.LoginUserSchema, Authorize):
        user = await user_service.verify_user_credentials(
            login_user_schema.email, login_user_schema.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect Email or Password",
            )

        access_token = Authorize.create_access_token(
            subject=str(user["id"]),
            expires_time=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_IN),
        )
        refresh_token = Authorize.create_refresh_token(
            subject=str(user["id"]),
            expires_time=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRES_IN),
        )

        # await user_service.update_user_login(user, access_token, refresh_token)

        return {
            "status": "success",
            "access_token": access_token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "role": user["role"],
                "photo": user["photo"],
                "email": user["email"],
            },
        }

    # Similarly implement refresh_token and logout methods
    async def refresh_access_token(response: Response, Authorize):
        try:
            Authorize.jwt_refresh_token_required()
            user_id = Authorize.get_jwt_subject()
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not refresh access token",
                )
            user = await user_service.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="The user belonging to this token no longer exists",
                )
            access_token = Authorize.create_access_token(
                subject=str(user["id"]),
                expires_time=timedelta(minutes=UserService.ACCESS_TOKEN_EXPIRES_IN),
            )

        except Exception as e:
            error = e.__class__.__name__
            if error == "MissingTokenError":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please provide refresh token",
                )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        response.set_cookie(
            "access_token",
            access_token,
            UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
            UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
            "/",
            None,
            False,
            True,
            "lax",
        )
        response.set_cookie(
            "logged_in",
            "True",
            UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
            UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
            "/",
            None,
            False,
            False,
            "lax",
        )
        return {"access_token": access_token}

    @staticmethod
    def logout(response: Response, Authorize, user_id: str):
        Authorize.unset_jwt_cookies()
        response.set_cookie("logged_in", "", -1)
        return {"status": "success"}
