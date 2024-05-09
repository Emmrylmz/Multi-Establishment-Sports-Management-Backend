from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.database import Event  # Assuming 'Event' is your MongoDB collection
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService


class TeamService(MongoDBService):
    def __init__(self, collection: Collection):
        super().__init__(collection)

    async def create(self, data: dict):
        # Add any event-specific logic before creating an event
        print("Additional logic before creating an event")
        return await super().create(data)
    
    async def update(self, doc_id: ObjectId, update_data: dict):
        # Add any event-specific logic before updating an event
        print("Additional logic before updating an event")
        return await super().update(doc_id, update_data)
    
    async def add_player_to_team(self, team_id: str, player_name: str):
        """Adds a player to the team's player list."""
        player_add = {"team_players": player_name}
        return await self.update_team(team_id, player_add)

    # def entity(self, document: dict):
    #     # Customize how event documents are transformed before they are returned
    #     if document:
    #         document["start_date"] = document["start_date"].strftime(
    #             "%Y-%m-%d %H:%M:%S"
    #         )
    #     return super().entity(document)

    # Add event-specific methods if necessary
    def get_upcoming_events(self):
        return self.list({"start_date": {"$gte": datetime.utcnow()}})
