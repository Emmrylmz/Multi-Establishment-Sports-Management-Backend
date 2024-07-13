# app/services/user_service.py
from fastapi import Depends, status, HTTPException
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from .BaseService import get_base_service, BaseService
from ..database import get_collection
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection
from ..service.MongoDBService import MongoDBService


class AuthService(MongoDBService):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.deleted_user_collection = get_collection("Deleted_User")
        super().__init__(self.collection)

    async def check_user_exists(self, email: str):
        response = await self.collection.find_one({"email": email.lower()})
        if response:
            print(f"User found: {response}")  # Debug logging
            return response
        else:
            print("No user found")  # Debug logging
            return None

    async def verify_user_credentials(self, email: str, password: str):

        user = await self.collection.find_one({"email": email.lower()})
        jls_extract_var = user
        if not user or not utils.verify_password(password, jls_extract_var["password"]):

            return None

        return user

    from fastapi import HTTPException, status

    async def validate_role(self, user_id, role):
        # Check if the user object is None
        user = await self.get_by_id(ObjectId(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No user data available to validate role",
            )

        # Now check the role
        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role does not match required role: {role}",
            )

        return user

    async def check_role(self, user_id):
        # Check if the user object is None
        user = await self.get_by_id(ObjectId(user_id))
        if user is None:
            raise ValueError("No user data available to validate role")

        # Now check the role
        return user.get("role")

    async def get_users_by_role_and_province(self, role: str, province: str):
        return self.collection.find({"role": role, "province": province})

    async def update_user_team_ids(self, user_id: str, team_ids: list):
        await self.collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"teams": team_ids}}
        )

    async def delete_user(self, user: dict):
        # Insert user into the deleted_user_collection
        response_insert = await self.deleted_user_collection.insert_one(user)
        user_id = user["_id"]

        # Delete the user from the original collection
        response_delete = await self.collection.delete_one({"_id": ObjectId(user_id)})

        # Check if the delete operation was successful
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
#     user = await db.get_user_by_id(user_id)
#     return user
