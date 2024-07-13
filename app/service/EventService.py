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
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.attendance_collection = get_collection("Attendance")
        self.private_lesson_collection = get_collection("Private_Lesson")
        self.user_collection = get_collection("User_Info")
        super().__init__(self.collection)

    async def get_all_events_by_team_id(
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
                            "start_datetime": "$start_datetime",
                            "end_datetime": "$end_datetime",
                            "description": "$description",
                            "team_id": "$team_id",
                        }
                    },
                }
            },
            {"$project": {"_id": 0, "team_id": "$_id", "team_name": 1, "events": 1}},
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        return results

    async def add_attendance(self, event_id, attendances):
        attendance_records = []
        for attendance in attendances:
            attendance_record = {
                "event_id": ObjectId(event_id),
                "user_id": attendance.user_id,
                "status": attendance.status,
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
        user_ids = set()  # Using a set for faster lookups

        for attendance in attendances:
            user_id = ObjectId(attendance.user_id)
            user_ids.add(user_id)
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

            bulk_operations.append(UpdateOne({"_id": user_id}, update_operation))

        try:
            if bulk_operations:
                result = await self.user_collection.bulk_write(bulk_operations)
                print(f"Modified {result.modified_count} document(s)")

            # Now update the ratios using an aggregation pipeline
            pipeline = [
                {"$match": {"_id": {"$in": list(user_ids)}}},
                {
                    "$addFields": {
                        f"{event_type}_attendance_ratio": {
                            "$round": [
                                {
                                    "$cond": [
                                        {"$eq": [f"$total_{event_type}_events", 0]},
                                        0,
                                        {
                                            "$divide": [
                                                f"$present_{event_type}_events",
                                                f"$total_{event_type}_events",
                                            ]
                                        },
                                    ]
                                },
                                2,  # Round to 2 decimal places
                            ]
                        }
                    }
                },
                {
                    "$merge": {
                        "into": self.user_collection.name,
                        "on": "_id",
                        "whenMatched": "merge",
                        "whenNotMatched": "discard",
                    }
                },
            ]

            await self.user_collection.aggregate(pipeline).to_list(None)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update attendance counts and ratios: {str(e)}",
            )

    # async def update_attendance_ratios(self, event_type, user_ids):
    #     try:
    #         for user_id in user_ids:
    #             user = await self.user_collection.find_one({"_id": ObjectId(user_id)})
    #             if user:
    #                 if event_type == "game":
    #                     total_events = user.get("total_game_events", 0)
    #                     present_events = user.get("present_game_events", 0)
    #                     ratio_field = "game_attendance_ratio"
    #                 elif event_type == "training":
    #                     total_events = user.get("total_training_events", 0)
    #                     present_events = user.get("present_training_events", 0)
    #                     ratio_field = "training_attendance_ratio"
    #                 else:
    #                     raise ValueError(f"Invalid event type: {event_type}")

    #                 attendance_ratio = (
    #                     present_events / total_events if total_events > 0 else 0
    #                 )

    #                 formatted_attendance_ratio = "{:.2f}".format(attendance_ratio)

    #                 await self.user_collection.update_one(
    #                     {"_id": ObjectId(user_id)},
    #                     {"$set": {ratio_field: formatted_attendance_ratio}},
    #                 )

    #     except Exception as e:
    #         raise HTTPException(
    #             status_code=500,
    #             detail=f"Failed to update attendance ratios: {str(e)}",
    #         )

    async def get_attendances_by_event_id(self, event_id):
        attendances = await self.attendance_collection.find(
            {"event_id": ObjectId(event_id)}
        ).to_list(length=None)
        return attendances

    async def get_upcoming_events(self, team_ids: List[str]):
        try:
            # Convert string IDs to ObjectId
            team_object_ids = [ObjectId(team_id) for team_id in team_ids]

            pipeline = [
                {
                    "$match": {
                        "team_id": {"$in": team_object_ids},
                        "start_datetime": {
                            "$gt": datetime.utcnow()
                        },  # Filter for upcoming events
                    }
                },
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
                                "start_datetime": "$start_datetime",
                                "end_datetime": "$end_datetime",
                                "description": "$description",
                                "team_id": {"$toString": "$team_id"},
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "team_id": {"$toString": "$_id"},
                        "team_name": 1,
                        "events": 1,
                    }
                },
            ]

            result = await self.collection.aggregate(pipeline).to_list(length=None)
            return result

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_attendance(self, event_id: str, event_type: str, new_attendances):
        event_object_id = ObjectId(event_id)

        # Fetch the event
        event = await self.collection.find_one({"_id": event_object_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Fetch existing attendance records for this event
        existing_attendances = await self.attendance_collection.find(
            {"event_id": event_object_id}
        ).to_list(None)

        existing_attendances_dict = {
            str(att["user_id"]): att["status"] for att in existing_attendances
        }

        attendance_updates = []
        user_updates = []

        for attendance in new_attendances:
            user_id = attendance.user_id
            new_status = attendance.status
            old_status = existing_attendances_dict.get(user_id, "absent")

            # Prepare attendance update
            attendance_updates.append(
                UpdateOne(
                    {"event_id": event_object_id, "user_id": user_id},
                    {"$set": {"status": new_status}},
                    upsert=True,
                )
            )

            # Prepare user update if status changed
            if old_status != new_status:
                if event_type in ["training", "game"]:
                    field_to_update = f"present_{event_type}_events"
                    update_value = 1 if new_status == "present" else -1

                    # Fetch the current user document
                    user = await self.user_collection.find_one(
                        {"_id": ObjectId(user_id)}
                    )

                    # Calculate new values
                    new_present_events = user.get(field_to_update, 0) + update_value
                    new_total_events = user.get(f"total_{event_type}_events", 0)

                    # Calculate the new ratio and round to 2 decimal places
                    new_ratio = round(
                        (
                            new_present_events / new_total_events
                            if new_total_events > 0
                            else 0
                        ),
                        2,
                    )

                    user_updates.append(
                        UpdateOne(
                            {"_id": ObjectId(user_id)},
                            {
                                "$inc": {field_to_update: update_value},
                                "$set": {f"{event_type}_attendance_ratio": new_ratio},
                            },
                        )
                    )

        # Perform bulk updates
        if attendance_updates:
            await self.attendance_collection.bulk_write(attendance_updates)
        if user_updates:
            await self.user_collection.bulk_write(user_updates)
            # Perform bulk updates
            if attendance_updates:
                await self.attendance_collection.bulk_write(attendance_updates)
            if user_updates:
                await self.user_collection.bulk_write(user_updates)

                # Execute bulk writes
                if attendance_updates:
                    await self.attendance_collection.bulk_write(attendance_updates)

                if user_updates:
                    await self.user_collection.bulk_write(user_updates)

                return {"message": "Attendance records updated successfully"}
                # Update overall attendance counts for the event

    async def create_privete_lesson(self, lesson_data: dict):
        result = await self.private_lesson_collection.insert_one(lesson_data)
        return await self.private_lesson_collection.find_one(
            {"_id": result.inserted_id}
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
