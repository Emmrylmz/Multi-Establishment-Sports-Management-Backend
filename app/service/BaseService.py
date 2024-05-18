from .MongoDBService import MongoDBService
from motor.motor_asyncio import AsyncIOMotorCollection
from ..database import Auth, Event, Team, Push_Token, User_Info


class BaseService(MongoDBService):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        super().__init__(collection)
        self.auth_collection = Auth
        self.event_collection = Event
        self.team_collection = Team
        self.push_token_collection = Push_Token
        self.user_info_collection = User_Info

    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        if collection_name == "auth":
            return self.auth_collection
        elif collection_name == "event":
            return self.event_collection
        elif collection_name == "team":
            return self.team_collection
        elif collection_name == "push_token":
            return self.push_token_collection
        elif collection_name == "user_info":
            return self.user_info_collection
        else:
            raise ValueError("Invalid collection name")
