# app/controllers/auth_controller.py

from fastapi import HTTPException, status
from ..models.user_schemas import (
    CreateUserSchema,
    LoginUserSchema,
    UserAttributesSchema,
    UserResponseSchema,
    User,
)
from fastapi import APIRouter, Response, status, Depends, HTTPException
from datetime import datetime, timedelta
from app.config import settings
from app import utils
from ..oauth2 import require_user
from ..models.firebase_token_schemas import PushTokenSchema
from .BaseController import BaseController


class AuthController(BaseController):

    async def register_user(self, payload: CreateUserSchema):
        if await self.auth_service.check_user_exists(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
            )

        if payload.password != payload.passwordConfirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
            )

        user_data = payload.dict(exclude_none=False)
        team_ids = payload.teams
        team_ids = [utils.ensure_object_id(team_id) for team_id in team_ids]
        user_data["teams"] = team_ids
        for team_id in payload.teams:
            if not await self.team_service.check_team_exists(team_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Team with id {team_id} not found",
                )

        hashed_password = self.hash_handler(user_data["password"])
        user_data["password"] = hashed_password
        user_data.pop("passwordConfirm", None)

        new_user = await self.auth_service.create(user_data)
        user_id = utils.ensure_object_id(new_user["_id"])
        user_dict = {k: v for k, v in new_user.items() if k != "password"}

        if len(payload.teams) > 0:

            user_role_field = (
                "team_players" if user_data["role"] == "Player" else "team_coaches"
            )
            result = await self.team_service.add_users_to_teams(
                user_ids=[user_id],
                team_ids=team_ids,
                user_role_field=user_role_field,
                register=True,
            )

            return {"status": "success", "user": user_dict, "result": result}

        return {"status": "success", "user": user_dict}

    async def login_user(self, payload: LoginUserSchema, Authorize):
        user = await self.auth_service.verify_user_credentials(
            payload.email, payload.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect Email or Password",
            )

        access_token = Authorize.create_access_token(
            subject=str(user["_id"]),
            expires_time=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_IN),
        )
        refresh_token = Authorize.create_refresh_token(
            subject=str(user["_id"]),
            expires_time=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRES_IN),
        )
        # self.auth_service.update_user_login(user, access_token, refresh_token)
        user_model = User(
            id=str(user["_id"]),
            name=user["name"],
            role=user["role"],
            email=user["email"],
            teams=user["teams"],
        )
        user_response = UserResponseSchema(
            status="success", access_token=access_token, user=user_model
        )

        return user_response

    # Similarly implement refresh_token and logout methods
    def refresh_access_token(self, response: Response, Authorize):
        try:
            Authorize.jwt_refresh_token_required()
            user_id = Authorize.get_jwt_subject()
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not refresh access token",
                )
            user = self.auth_service.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="The user belonging to this token no longer exists",
                )
            access_token = Authorize.create_access_token(
                subject=str(user["id"]),
                expires_time=timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRES_IN),
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
            auth_service.ACCESS_TOKEN_EXPIRES_IN * 60,
            auth_service.ACCESS_TOKEN_EXPIRES_IN * 60,
            "/",
            None,
            False,
            True,
            "lax",
        )
        response.set_cookie(
            "logged_in",
            "True",
            auth_service.ACCESS_TOKEN_EXPIRES_IN * 60,
            auth_service.ACCESS_TOKEN_EXPIRES_IN * 60,
            "/",
            None,
            False,
            False,
            "lax",
        )
        return {"access_token": access_token}

    def logout(self, response: Response, Authorize, user_id: str):
        Authorize.unset_jwt_cookies()
        response.set_cookie("logged_in", "", -1)
        return {"status": "success"}

    async def get_push_token(
        self, payload: PushTokenSchema, user: dict = Depends(require_user)
    ):
        try:
            user_id = user["_id"]
            result = await self.token_service.save_token(payload, user_id)
            return {"result": payload.dict()}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # @staticmethod
    # async def submit_user_attributes(payload: UserAttributesSchema, user):
    #     try:
    #         payload_data = payload.dict()
    #         user_id = user["_id"]
    #         payload_data["_id"] = user_id
    #         response = await auth_service.create(payload_data)
    #     except e:
    #         print(e)
