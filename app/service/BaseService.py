from motor.motor_asyncio import AsyncIOMotorCollection
from .MongoDBService import MongoDBService
from ..database import get_collection


class BaseService:
    def __init__(self):
        self.collections = {
            "Auth": get_collection("Auth"),
            "Event": get_collection("Event"),
            "Team": get_collection("Teams"),
            "Push_Token": get_collection("Push_Token"),
            "User_Info": get_collection("User_Info"),
        }

    def get_from_collections(self, collection_name: str) -> AsyncIOMotorCollection:
        if collection_name in self.collections:
            return self.collections[collection_name]
        else:
            raise ValueError("Invalid collection name")


def get_base_service():
    return BaseService()
