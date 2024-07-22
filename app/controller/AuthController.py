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
from ..oauth2 import require_user
from ..models.firebase_token_schemas import PushTokenSchema
from .BaseController import BaseController
from ..service.AuthService import AuthService
from ..service.TokenService import PushTokenService
from ..service.TeamService import TeamService


class AuthController(BaseController):
    def __init__(
        self,
        auth_service: AuthService,
        token_service: PushTokenService,
        team_service: TeamService,
    ):
        super().__init__()  # This initializes the BaseController
        self.auth_service = auth_service
        self.token_service = token_service
        self.team_service = team_service

    async def register_user(self, payload: CreateUserSchema):
        if await self.auth_service.verify_user_credentials(
            payload.email, payload.password
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
            )

        if payload.password != payload.passwordConfirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
            )

        user_data = payload.dict(exclude_none=False)
        team_ids = payload.teams
        province = user_data.get("province")

        # If user role is manager, fetch all team ids
        if user_data.get("role") == "Manager" and province and len(province) > 0:
            team_ids = await self.team_service.get_all_teams_by_province(
                province=province
            )
        else:
            team_ids = [str(team_id) for team_id in team_ids]

        user_data["teams"] = team_ids
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
        user_id = self.format_handler(new_user["_id"])
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

    async def login_user(self, payload: LoginUserSchema, Authorize, response: Response):
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

        # Optionally, store the refresh token in the database or another secure location
        # await self.auth_service.store_refresh_token(user["_id"], refresh_token)

        # Set the refresh token as an HttpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=settings.REFRESH_TOKEN_EXPIRES_IN * 60,
            expires=settings.REFRESH_TOKEN_EXPIRES_IN * 60,
        )

        # Convert ObjectId to string for teams
        teams = [str(team_id) for team_id in user.get("teams", [])]

        user_model = User(
            id=str(user["_id"]),
            name=user["name"],
            role=user["role"],
            email=user["email"],
            teams=teams,
            province=user["province"],
        )
        user_response = UserResponseSchema(
            status="success",
            access_token=access_token,
            refresh_token=refresh_token,  # Include refresh token in response
            user=user_model,
        )

        return user_response

    # Similarly implement refresh_token and logout methods
    async def refresh_access_token(self, response: Response, Authorize):
        try:
            Authorize.jwt_required()
            user_id = Authorize.get_jwt_subject()
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not refresh access token",
                )
            user = await self.auth_service.get_user_by_id(user_id)
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

    def logout(self, response: Response, Authorize):
        try:
            Authorize.jwt_required()
        except Exception as e:
            # Log the exception if needed
            print(f"Exception during JWT validation: {e}")

        # Always clear cookies regardless of JWT validation result
        Authorize.unset_jwt_cookies()
        response.set_cookie("logged_in", "", -1)
        return {"status": "success"}

    async def get_push_token(
        self, payload: PushTokenSchema, user_id: str = Depends(require_user)
    ):
        user = await self.auth_service.get_by_id(self.format_handler(user_id))
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

    async def delete_user(self, user_id: str):
        try:
            user_id_obj = self.format_handler(user_id)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid user ID format: {str(e)}"
            )
        try:
            # Check if the user exists
            user = await self.auth_service.get_by_id(user_id_obj)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            deleted_user = await self.auth_service.delete_user(user)
            deleted_team = await self.team_service.remove_user_from_teams(
                user_id_obj, user["teams"]
            )
            return {"deleted_user": deleted_user, "deleted_team": deleted_team}
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
