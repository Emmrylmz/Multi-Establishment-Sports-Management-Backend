from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from ..models.firebase_token_schemas import PushTokenSchema
from .MongoDBService import MongoDBService
from .BaseService import BaseService
from ..database import get_collection


class PushTokenService(MongoDBService):
    def __init__(
        self,
        collection: AsyncIOMotorCollection = Depends(
            lambda: get_collection("Push_Token")
        ),
    ):
        self.collection = collection
        self.team_collection = get_collection("Team")
        super().__init__(self.collection)

    async def save_token(self, payload: PushTokenSchema, user_id: str):
        data = payload.dict()
        token = await self.get_by_id(user_id)
        if token:
            res = await self.update(user_id, {"token": payload.token})
            return res
        data["_id"] = ObjectId(user_id)
        result = await self.create(data)
        return result

    async def get_team_player_tokens(self, team_id):
        try:
            team = await self.team_collection.find_one({"_id": ObjectId(team_id)})
            if team:
                players_ids = team["team_players"]
                object_ids = [ObjectId(id) for id in players_ids]
                query = {"_id": {"$in": object_ids}}
                documents = await self.list(query=query)
                tokens = [player["token"] for player in documents if "token" in player]
                return tokens
            else:
                return {"team not found"}
        except KeyError as e:
            print(f"Key error: {e} - Check data integrity")
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []
