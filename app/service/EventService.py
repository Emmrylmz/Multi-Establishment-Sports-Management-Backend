from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from ..config import settings
from ..database import get_collection
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi import Depends, HTTPException
from ..utils import ensure_object_id
from ..service.BaseService import BaseService, get_base_service
from typing import List, Dict, Any
from pymongo import UpdateOne


class EventService(MongoDBService):
    def __init__(
        self,
        collection: AsyncIOMotorCollection = Depends(lambda: get_collection("Event")),
    ):
        self.collection = collection
        self.attendance_collection = get_collection("Attendance")
        self.user_collection = get_collection("User_Info")
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

    async def add_attendance(self, event_id, attendances, event_type, team_id):
        attendance_records = []
        for attendance in attendances:
            attendance_record = {
                "event_id": ObjectId(event_id),
                "user_id": attendance.user_id,
                "status": attendance.status,
                "event_type": event_type,
                "team_id": team_id,
                "timestamp": datetime.now(),
            }
            attendance_records.append(attendance_record)

        try:
            await self.attendance_collection.insert_many(attendance_records)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to insert attendance records: {str(e)}"
            )

        return attendance_records

    async def update_attendance_counts(self, event_type, attendances):
        bulk_operations = []
        user_ids = []

        for attendance in attendances:
            user_id = attendance.user_id
            user_ids.append(user_id)
            present_increment = 1 if attendance.status == "present" else 0

            if event_type == "game":
                update_operation = {
                    "$inc": {
                        "total_game_events": 1,
                        "present_game_events": present_increment,
                    }
                }
            elif event_type == "training":
                update_operation = {
                    "$inc": {
                        "total_training_events": 1,
                        "present_training_events": present_increment,
                    }
                }
            else:
                raise ValueError(f"Invalid event type: {event_type}")

            # Add the update operation to bulk operations
            bulk_operations.append(
                UpdateOne({"_id": ObjectId(user_id)}, update_operation)
            )

        try:
            if bulk_operations:
                result = await self.user_collection.bulk_write(bulk_operations)
                print(f"Modified {result.modified_count} document(s)")

            # Update the ratios
            await self.update_attendance_ratios(event_type, user_ids)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update attendance counts and ratios: {str(e)}",
            )

    async def update_attendance_ratios(self, event_type, user_ids):
        try:
            for user_id in user_ids:
                user = await self.user_collection.find_one({"_id": ObjectId(user_id)})
                if user:
                    if event_type == "game":
                        total_events = user.get("total_game_events", 0)
                        present_events = user.get("present_game_events", 0)
                        ratio_field = "game_attendance_ratio"
                    elif event_type == "training":
                        total_events = user.get("total_training_events", 0)
                        present_events = user.get("present_training_events", 0)
                        ratio_field = "training_attendance_ratio"
                    else:
                        raise ValueError(f"Invalid event type: {event_type}")

                    attendance_ratio = (
                        present_events / total_events if total_events > 0 else 0
                    )

                    await self.user_collection.update_one(
                        {"_id": ObjectId(user_id)},
                        {"$set": {ratio_field: attendance_ratio}},
                    )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update attendance ratios: {str(e)}",
            )


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
