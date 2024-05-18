from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from ..config import settings
from ..database import Event


class EventService(MongoDBService):
    def __init__(self):
        super().__init__(Event)

    # async def list_events(self, team_id: dict):
    #     query = {"team_id": team_id}
    #     events = await event_service.list(query)
    #     return events

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
