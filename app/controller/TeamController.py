from fastapi import (
    HTTPException,
    status,
    APIRouter,
    Response,
    status,
    Depends,
    HTTPException,
    Request,
)
from ..models.team_schemas import CreateTeamSchema
from datetime import datetime, timedelta
from app.config import settings
from app import utils
from ..oauth2 import require_user
from ..service.TeamService import TeamService
from ..service.UserService import UserService
from ..database import Team

team_service = TeamService(Team)


class TeamController:
    @staticmethod
    async def register_team(
        team_payload: CreateTeamSchema,
        request: Request,
        user: dict = Depends(require_user),
    ):

        app = request.app
        UserService.validate_role(user, "Coach")
        team_data = team_payload.dict()
        created_team = await team_service.create(team_data)
        if not created_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_BAD_REQUEST,
                detail="Could not create team",
            )
        # If created_event is a Pydantic model, return its .dict(), otherwise return it directly if it's already a dict
        await app.rabbit_client.start_subscription(queue_name=team_data["team_id"])
        return created_team

    # @staticmethod
    # def login_user(login_user_schema: schemas.LoginUserSchema, Authorize):
    #     user = UserService.verify_user_credentials(
    #         login_user_schema.email, login_user_schema.password
    #     )
    #     if not user:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Incorrect Email or Password",
    #         )

    #     access_token = Authorize.create_access_token(
    #         subject=str(user["id"]),
    #         expires_time=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_IN),
    #     )
    #     refresh_token = Authorize.create_refresh_token(
    #         subject=str(user["id"]),
    #         expires_time=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRES_IN),
    #     )

    #     UserService.update_user_login(user, access_token, refresh_token)

    #     return {
    #         "status": "success",
    #         "access_token": access_token,
    #         "user": {
    #             "id": user["id"],
    #             "name": user["name"],
    #             "role": user["role"],
    #             "photo": user["photo"],
    #             "email": user["email"],
    #         },
    #     }

    # # Similarly implement refresh_token and logout methods
    # def refresh_access_token(response: Response, Authorize):
    #     try:
    #         Authorize.jwt_refresh_token_required()
    #         user_id = Authorize.get_jwt_subject()
    #         if not user_id:
    #             raise HTTPException(
    #                 status_code=status.HTTP_401_UNAUTHORIZED,
    #                 detail="Could not refresh access token",
    #             )
    #         user = UserService.get_user_by_id(user_id)
    #         if not user:
    #             raise HTTPException(
    #                 status_code=status.HTTP_401_UNAUTHORIZED,
    #                 detail="The user belonging to this token no longer exists",
    #             )
    #         access_token = Authorize.create_access_token(
    #             subject=str(user["id"]),
    #             expires_time=timedelta(minutes=UserService.ACCESS_TOKEN_EXPIRES_IN),
    #         )

    #     except Exception as e:
    #         error = e.__class__.__name__
    #         if error == "MissingTokenError":
    #             raise HTTPException(
    #                 status_code=status.HTTP_400_BAD_REQUEST,
    #                 detail="Please provide refresh token",
    #             )
    #         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    #     response.set_cookie(
    #         "access_token",
    #         access_token,
    #         UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
    #         UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
    #         "/",
    #         None,
    #         False,
    #         True,
    #         "lax",
    #     )
    #     response.set_cookie(
    #         "logged_in",
    #         "True",
    #         UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
    #         UserService.ACCESS_TOKEN_EXPIRES_IN * 60,
    #         "/",
    #         None,
    #         False,
    #         False,
    #         "lax",
    #     )
    #     return {"access_token": access_token}

    # @staticmethod
    # def logout(response: Response, Authorize, user_id: str):
    #     Authorize.unset_jwt_cookies()
    #     response.set_cookie("logged_in", "", -1)
    #     return {"status": "success"}
