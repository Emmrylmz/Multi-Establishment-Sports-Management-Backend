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
