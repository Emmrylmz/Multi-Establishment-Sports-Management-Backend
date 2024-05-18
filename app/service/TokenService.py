from bson import ObjectId
from pymongo.collection import Collection
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from ..models.firebase_token_schemas import PushTokenSchema
from ..database import Push_Token


class PushTokenService(MongoDBService):
    def __init__(self):
        super().__init__(Push_Token)

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
            team = await team_service.get_by_id(ObjectId(team_id))

            if team:
                players_ids = team["team_players"]
                object_ids = [ObjectId(id) for id in players_ids]
                query = {"_id": {"$in": object_ids}}
                documents = await self.list(query=query)
                # Extract tokens, ensuring each player has a token attribute
                tokens = [player["token"] for player in documents if "token" in player]

                return tokens
            else:
                return {"team not found"}
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
