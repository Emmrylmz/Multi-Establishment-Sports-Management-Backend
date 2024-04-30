# app/services/user_service.py

from app.database import User
from app.serializers.userSerializer import userEntity, userResponseEntity
from .. import utils
from datetime import datetime
from bson import ObjectId


class UserService:
    @staticmethod
    def check_user_exists(email: str):
        return User.find_one({"email": email.lower()})

    @staticmethod
    def create_user(user_data: dict):
        user_data["created_at"] = datetime.utcnow()
        result = User.insert_one(user_data)
        return User.find_one({"_id": result.inserted_id})

    @staticmethod
    def verify_user_credentials(email: str, password: str):
        user = User.find_one({"email": email.lower()})
        if not user or not utils.verify_password(password, user["password"]):
            return None
        return userEntity(user)

    @staticmethod
    def get_user_by_id(user_id: str):
        return userEntity(User.find_one({"_id": ObjectId(user_id)}))

    @staticmethod
    def update_user_login(user_id: str, access_token: str, refresh_token: str):
        # Here you can update any login related fields in the user model if necessary
        pass
