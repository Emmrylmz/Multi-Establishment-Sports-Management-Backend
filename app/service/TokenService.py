from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from app.service.UserService import user_service
from ..models.firebase_token_schemas import PushTokenSchema
from ..service.TeamService import team_service
import asyncio
from typing import List
from ..database import Push_Token
from fastapi.encoders import jsonable_encoder


class PushTokenService(MongoDBService):
    def __init__(self, collection: Collection):
        super().__init__(collection)

    async def save_token(self, payload: PushTokenSchema, user_id: str):
        data = payload.dict()
        data["_id"] = ObjectId(user_id)
        result = await self.create(data)
        return result.inserted_id

    async def get_team_player_tokens(self, team_id: str) -> List[str]:
        try:
            team = await team_service.get_by_id(team_id)

            players_ids = team["team_players"]

            object_ids = [ObjectId(id) for id in players_ids]

            query = {"_id": {"$in": object_ids}}

            documents = await self.list(query=query)

            # Extract tokens, ensuring each player has a token attribute
            tokens = [player["token"] for player in documents if "token" in player]

            return tokens
        except Exception as e:
            # Handle possible exceptions
            print(f"An error occurred: {e}")
            return []
        except KeyError as e:
            # Handle cases where expected keys are missing in the data
            print(f"Key error: {e} - Check data integrity")
            return []
        except Exception as e:
            # Generic exception handling to catch unexpected errors
            print(f"An error occurred: {e}")
            return []


push_token_service = PushTokenService(Push_Token)
