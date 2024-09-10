# event_repository.py
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
from typing import List, Dict, Optional
from pymongo import UpdateOne
from datetime import datetime
from ..database import get_collection
from ..models.event_schemas import ListEventParams, CreateEventSchema


class EventRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = None
        self.attendance_collection = None
        self.private_lesson_collection = None
        self.user_collection = None

    @classmethod
    async def initialize(cls, database: AsyncIOMotorDatabase):
        self = cls(database)
        self.collection = await get_collection("Event", database)
        self.attendance_collection = await get_collection("Attendance", database)
        self.private_lesson_collection = await get_collection(
            "Private_Lesson", database
        )
        self.user_collection = await get_collection("User_Info", database)
        return self

    async def create_event(self, event: CreateEventSchema):
        result = await self.collection.insert_one(event)
        return result.inserted_id

    async def get_private_lesson_by_id(self, private_lesson_id: str):
        return await self.private_lesson_collection.find_one({"_id": private_lesson_id})

    async def get_event_by_id(self, event_id: str):
        return await self.collection.find_one({"_id": ObjectId(event_id)})

    async def get_event_by_team_ids(
        self,
        team_object_ids: List[ObjectId],
        skip: int,
        limit: int,
        projection: Optional[Dict] = None,
    ):
        query = {"team_id": {"$in": team_object_ids}}
        total_events = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query, projection)
            .sort("start_datetime", 1)
            .skip(skip)
            .limit(limit)
        )
        events = await cursor.to_list(length=limit)
        return total_events, events

    async def insert_attendances(self, attendances: List[Dict]):
        return await self.attendance_collection.insert_many(attendances)

    async def get_attendances_by_event_id(
        self,
        event_id: str,
        query: Dict,
        projection: Optional[Dict] = None,
        limit: int = 20,
    ):
        cursor = (
            self.attendance_collection.find(query, projection=projection)
            .sort("_id", 1)
            .limit(limit + 1)
        )
        attendances = await cursor.to_list(length=None)
        return attendances

    async def bulk_update_attendance(self, bulk_operations: List[UpdateOne]):
        return await self.attendance_collection.bulk_write(bulk_operations)

    async def insert_private_lesson(self, lesson_data: Dict):
        result = await self.private_lesson_collection.insert_one(lesson_data)
        return result.inserted_id

    async def update_private_lesson(self, lesson_id: str, update_data: dict):
        result = await self.private_lesson_collection.update_one(
            {"_id": ObjectId(lesson_id)}, {"$set": update_data}
        )
        return result.modified_count

    async def get_private_lessons_by_user(self, id: str, field: str):
        query = {field: id}
        cursor = self.private_lesson_collection.find(query)
        return await cursor.to_list(length=None)

    async def get_events_for_teams(self, params: ListEventParams):
        pipeline = self._build_pipeline(params)
        logger.debug(f"MongoDB Aggregation Pipeline: {pipeline}")

        result = await self.collection.aggregate(pipeline).to_list(length=None)
        logger.debug(f"Aggregation Result: {result}")

    def _build_pipeline(self, params: ListEventParams):
        match_stage = self._build_match_stage(params)
        sort_order = -1 if params.sort_order == "desc" else 1

        pipeline = [
            match_stage,
            {"$sort": {"start_datetime": sort_order}},
            {
                "$lookup": {
                    "from": "Team",  # Make sure this matches your actual collection name
                    "let": {"team_id": {"$toObjectId": "$team_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$team_id"]}}},
                        {"$project": {"team_name": 1, "_id": 0}},
                    ],
                    "as": "team_info",
                }
            },
            {
                "$addFields": {
                    "team_name": {
                        "$ifNull": [
                            {"$arrayElemAt": ["$team_info.team_name", 0]},
                            "Unknown Team",  # Default value if team is not found
                        ]
                    }
                }
            },
            {
                "$project": {
                    "event_id": {"$toString": "$_id"},
                    "description": 1,
                    "event_type": 1,
                    "place": 1,
                    "start_datetime": 1,
                    "end_datetime": 1,
                    "created_at": 1,
                    "creator_id": 1,
                    "team_id": 1,
                    "team_name": 1,
                }
            },
            {
                "$group": {
                    "_id": None,
                    "events": {"$push": "$$ROOT"},
                    "total_count": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "events": {
                        "$slice": [
                            "$events",
                            (params.page - 1) * params.page_size,
                            params.page_size,
                        ]
                    },
                    "total_count": 1,
                }
            },
        ]
        return pipeline

    def _build_match_stage(self, params: ListEventParams):
        match_conditions = {}
        if params.team_ids:
            match_conditions["team_id"] = {
                "$in": params.team_ids
            }  # Remove ObjectId conversion
        # if params.user_id:
        #     match_conditions["creator_id"] = params.user_id

        # Add a date range check if needed
        match_conditions["end_datetime"] = {"$gt": datetime.utcnow()}

        logger.debug(f"Match conditions: {match_conditions}")
        return {"$match": match_conditions}
