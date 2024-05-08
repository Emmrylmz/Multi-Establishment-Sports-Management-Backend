# app/services/user_service.py
from fastapi import Depends
from app.serializers.userSerializer import userEntity, userResponseEntity
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from .MongoDBService import MongoDBService
from ..database import User
from pymongo.collection import Collection


class UserService(MongoDBService):
    def __init__(self, collection: Collection):
        super().__init__(collection=collection)

    async def check_user_exists(self, email: str):

        return await self.collection.find_one({"email": email.lower()})

    async def verify_user_credentials(self, email: str, password: str):

        user = await self.collection.find_one({"email": email.lower()})
        jls_extract_var = user
        if not user or not utils.verify_password(password, jls_extract_var["password"]):

            return None

        return userEntity(user)

    async def validate_role(self, user, role):
        # Check if the user object is None
        if user is None:
            raise ValueError("No user data available to validate role")

        # Now check the role
        if user.get("role") != role:
            raise ValueError(f"User role does not match required role: {role}")


user_service = UserService(User)


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
#     user = await db.get_user_by_id(user_id)
#     return user
