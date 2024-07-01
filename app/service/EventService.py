from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from ..config import settings
from ..database import get_collection
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi import Depends
from ..utils import ensure_object_id
from ..service.BaseService import BaseService, get_base_service
from typing import List, Dict, Any


class EventService(MongoDBService):
    def __init__(
        self,
        collection: AsyncIOMotorCollection = Depends(lambda: get_collection("Event")),
    ):
        self.collection = collection
        super().__init__(self.collection)

    async def get_upcoming_events(
        self, team_object_ids: List[ObjectId]
    ) -> List[Dict[str, Any]]:
        pipeline = [
            {"$match": {"team_id": {"$in": team_object_ids}}},
            {
                "$lookup": {
                    "from": "Team",
                    "localField": "team_id",
                    "foreignField": "_id",
                    "as": "team_info",
                }
            },
            {"$unwind": "$team_info"},
            {
                "$group": {
                    "_id": "$team_id",
                    "team_name": {"$first": "$team_info.team_name"},
                    "events": {
                        "$push": {
                            "event_id": {"$toString": "$_id"},
                            "event_type": "$event_type",
                            "place": "$place",
                            "event_date": "$event_date",
                            "description": "$description",
                        }
                    },
                }
            },
            {"$project": {"_id": 0, "team_id": "$_id", "team_name": 1, "events": 1}},
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        return results


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
