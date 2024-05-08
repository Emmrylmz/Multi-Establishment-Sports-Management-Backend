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


class PushTokenService(MongoDBService):
    def __init__(self, collection: str):
        super().__init__(collection)

    def save_token(self, payload: PushTokenSchema, user_id: str):
        data = payload.dict()
        data["_id"] = ObjectId(user_id)
        result = self.collection.insert_one(data)
        return result.inserted_id  #

    async def get_team_player_tokens(self, team_id: str) -> List[str]:
        try:
            # Assume get_by_id is an async function that fetches the team data
            team = await team_service.get_by_id(team_id)
            players = team["team_players"]

            # Utilize asyncio.gather to fetch all player data concurrently
            # This assumes self.collection.get_by_id is an async function
            player_fetch_tasks = [
                self.collection.get_by_id(player) for player in players
            ]
            players_data = await asyncio.gather(*player_fetch_tasks)

            # Extract tokens, ensuring each player has a token attribute
            tokens = [player["token"] for player in players_data if "token" in player]
            return tokens

        except KeyError as e:
            # Handle cases where expected keys are missing in the data
            print(f"Key error: {e} - Check data integrity")
            return []
        except Exception as e:
            # Generic exception handling to catch unexpected errors
            print(f"An error occurred: {e}")
            return []


push_token_service = PushTokenService(collection="push_token")
