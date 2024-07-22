# app/services/user_service.py
from fastapi import Depends, Query
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection
from ..service.MongoDBService import MongoDBService
from ..database import get_collection
from typing import List


class UserService(MongoDBService):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.collection = get_collection("User_Info")
        super().__init__(self.collection)

    async def get_users_by_id(self, player_ids):
        # Query all users at once using the $in operator
        cursor = self.collection.find(
            {"_id": {"$in": player_ids}},
            {"name": 1, "photo": 1, "_id": 1, "discount": 1},
        )

        # Convert cursor to list
        user_infos = await cursor.to_list(length=None)

        return user_infos

    # async def get_discount_by_user_id(self, user_id):
    #     user_discount = await self.collection.find_one(
    #         {"_id": ObjectId(user_id)}, {"discount": 1, "_id": 0}
    #     )

    #     return user_discount.get("dues", 0)

    async def search_users_by_name(self, query: str):
        # Create a case-insensitive regex pattern
        pattern = f".*{query}.*"
        regex = {"$regex": pattern, "$options": "i"}

        # Search for users whose name matches the query
        users = await self.collection.find(
            {"name": regex}, {"_id": 1, "name": 1, "photo": 1}
        ).to_list(length=None)
        return users


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
