# app/services/user_service.py
from fastapi import Depends, status, HTTPException
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from ..database import get_collection, get_database
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from ..redis_client import RedisClient
from bson.json_util import dumps, loads
from typing import List, Optional, Dict, Any
from ..models.user_schemas import UserRole
from app.celery_app.celery_tasks import invalidate_caches
from ..repositories.AuthRepository import AuthRepository
from pymongo.client_session import ClientSession


class AuthService:
    @classmethod
    async def initialize(
        cls, auth_repository: AuthRepository, redis_client: RedisClient
    ):
        self = cls.__new__(cls)
        await self.__init__(auth_repository, redis_client)
        return self

    async def __init__(
        self, auth_repository: AuthRepository, redis_client: RedisClient
    ):
        self.redis_client = redis_client
        self.auth_repository = auth_repository

    async def create_user(
        self, user_data: Dict[str, Any], session: Optional[ClientSession] = None
    ) -> Dict[str, Any]:
        return await self.auth_repository.create_user(user_data, session)

    async def check_user_exists(self, email: str) -> Optional[Dict[str, Any]]:
        user = await self.auth_repository.find_user_by_email(email)
        if user:
            return user
        return None

    async def verify_user_credentials(
        self, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        user = await self.check_user_exists(email)
        if not user or not utils.verify_password(password, user["password"]):
            return None
        return user

    async def validate_role(self, user_id: str, role: "str") -> Dict[str, Any]:
        user = await self.auth_repository.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No user data available to validate role",
            )

        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role does not match required role: {role}",
            )

        return user

    async def check_role(self, user_id: str) -> str:
        user = await self.auth_repository.get_user_by_id(user_id)
        if user is None:
            raise ValueError("No user data available to validate role")
        return user.get("role")

    # async def get_users_by_role_and_province(
    #     self,
    #     role: UserRole,
    #     province: str,
    #     skip: int = 0,
    #     limit: int = 20,
    #     fields: Optional[List[str]] = None,
    # ) -> List[Dict[str, Any]]:

    #     projection = {field: 1 for field in fields} if fields else None
    #     users = (
    #         await self.collection.find(
    #             {"role": role, "province": province}, projection=projection
    #         )
    #         .skip(skip)
    #         .limit(limit)
    #         .to_list(None)
    #     )
    #     return users

    async def update_user_team_ids(self, user_id: str, team_ids: List[str]):
        modified_count = await self.auth_repository.update_user(
            user_id=user_id, update_data={"teams": team_ids}
        )
        return modified_count

    async def delete_user(self, user: Dict[str, Any], session) -> Dict[str, Any]:

        response_delete, response_insert = await self.auth_repository.delete_user(
            user=user, session=session
        )

        if response_delete.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete user")

        return {
            "deleted_count": response_delete.deleted_count,
            "inserted_id": str(response_insert.inserted_id),
        }


# @staticmethod
# def get_current_user(token: str = Depends(user_service.get_current_user_token)):
#     """

#     Dependency function to get the current user based on the provided token.

#     This assumes you have a method `get_current_user_token` in UserService

#     or another service that can retrieve the user's token.
#     """

#     # Assuming UserService returns a User object or None if user not found

#     current_user = user_service.get_user_by_token(token)

#     if current_user is None:

#         # Raise HTTPException if user is not authenticated

#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#         return current_user

# @staticmethod
# async def get_current_user(self, token: str = Depends(verify_token)):
#     """
#     Dependency function to get the current user based on the provided JWT token.
#     """
#     # Assuming verify_token returns a dict with user data or None if token is invalid
#     user_data = await self.verify_token(token)

#     if user_data is None:
#         # Raise HTTPException if token is invalid or user not found
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     # Assuming you have a method to get the user from the user data
#     current_user = await self.get_user_by_data(user_data)

#     if current_user is None:
#         # Raise HTTPException if user not found
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     return current_user

# async def get_user_by_data(self, user_data: dict) -> User:
#     """
#     Method to get the user object based on user data extracted from JWT token.
#     This is just a placeholder. You should replace it with your actual user retrieval logic.
#     """
#     # Assuming you have a method to get the user object from the user data in the token
#     # Replace this with your actual user retrieval logic based on user data
#     # For example, if user_data contains user ID, you can retrieve the user object from the database
#     # Here's a simplified example assuming user data contains user ID
#     user_id = user_data.get("user_id")
#     # Assuming you have a database connection and a method to get the user by ID
#     # Replace this with your actual database query
#     user = await db.auth_repository.get_user_by_id(user_id)
#     return user
