from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from ..models.firebase_token_schemas import PushTokenSchema
from .MongoDBService import MongoDBService
from ..database import get_collection


class PushTokenService(MongoDBService):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.team_collection = get_collection("Team")
        super().__init__(self.collection)

    async def save_token(self, payload: PushTokenSchema, user_id: str):
        try:
            data = payload.dict()
            token = await self.collection.find_one({"_id": ObjectId(user_id)})
            if token:
                res = await self.collection.update_one(
                    {"_id": ObjectId(user_id)}, {"$set": {"token": payload.token}}
                )
                return res.modified_count > 0
            data["_id"] = ObjectId(user_id)
            result = await self.collection.insert_one(data)
            return result.inserted_id is not None
        except Exception as e:
            logging.error(f"Error saving token: {e}")
            return False

    async def get_team_player_tokens(self, team_id):
        try:
            team = await self.team_collection.find_one({"_id": ObjectId(team_id)})
            if team:
                players_ids = team.get("team_players", [])
                object_ids = [ObjectId(id) for id in players_ids]
                query = {"_id": {"$in": object_ids}}
                documents = await self.collection.find(query).to_list(None)
                tokens = [
                    player.get("token") for player in documents if player.get("token")
                ]
                return tokens
            else:
                logging.warning(f"Team not found: {team_id}")
                return []
        except Exception as e:
            logging.error(f"Error getting team player tokens: {e}")
            return []

    async def get_user_token(self, user_id):
        try:
            token = await self.collection.find_one({"_id": ObjectId(user_id)})
            if not token:
                logging.warning(f"No user Push Token found for user: {user_id}")
                return None
            return token.get("token")
        except Exception as e:
            logging.error(f"Error getting user token: {e}")
            return None

    async def get_all_user_tokens(self):
        try:
            documents = await self.collection.find({}, {"token": 1, "_id": 0}).to_list(
                None
            )
            tokens = [doc.get("token") for doc in documents if doc.get("token")]
            return tokens
        except Exception as e:
            logging.error(f"Error getting all user tokens: {e}")
            return []

    async def get_province_user_tokens(self, province: str):
        try:
            query = {"province": province}
            documents = await self.collection.find(
                query, {"token": 1, "_id": 0}
            ).to_list(None)
            tokens = [doc.get("token") for doc in documents if doc.get("token")]
            return tokens
        except Exception as e:
            logging.error(f"Error getting province user tokens: {e}")
            return []
