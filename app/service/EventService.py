from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
from .MongoDBService import MongoDBService
from ..config import settings
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from fastapi import Depends, HTTPException, status, Request
from ..utils import ensure_object_id
from typing import List, Dict, Any
from pymongo import UpdateOne
from ..models.event_schemas import (
    CreatePrivateLessonSchema,
    RequestStatus,
    EventType,
    EventResponseSchema,
    ListEventResponseSchema,
    ListEventParams,
    ListEventResponseSchema,
)
from ..models.attendance_schemas import AttendanceFormSchema, AttendanceRecord
from ..redis_client import RedisClient
from ..database import get_database, get_collection
from bson.json_util import dumps, loads
from typing import Optional
from app.celery_app.celery_tasks import invalidate_caches
from redis.exceptions import RedisError
import json
from app.utils import JSONEncoder, logging

logger = logging.getLogger(__name__)


class EventService(MongoDBService):
    @classmethod
    async def initialize(
        cls, database: AsyncIOMotorDatabase, redis_client: RedisClient
    ):
        self = cls.__new__(cls)
        await self.__init__(database, redis_client)
        return self

    async def __init__(
        self,
        database: AsyncIOMotorDatabase,
        redis_client: RedisClient,
    ):
        self.database = database
        self.redis_client = redis_client

        # Initialize frequently used collections
        self.collection = await get_collection("Event", database)
        self.attendance_collection = await get_collection("Attendance", database)

        # Use properties for less frequently used collections
        self._private_lesson_collection = None
        self._user_collection = None

        await super().__init__(self.collection)

    @property
    async def private_lesson_collection(self):
        if self._private_lesson_collection is None:
            self._private_lesson_collection = await get_collection(
                "Private_Lesson", self.database
            )
        return self._private_lesson_collection

    @property
    async def user_collection(self):
        if self._user_collection is None:
            self._user_collection = await get_collection("User_Info", self.database)
        return self._user_collection

    async def get_private_lesson_by_id(self, private_lesson_id: str):
        collection = await self.private_lesson_collection
        return await collection.find_one({"_id": private_lesson_id})

    async def get_all_events_by_team_id(
        self,
        team_object_ids: List[ObjectId],
        page: int,
        events_per_page: int = 10,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        skip = (page - 1) * events_per_page

        query = {"team_id": {"$in": team_object_ids}}
        projection = {field: 1 for field in fields} if fields else None

        try:
            total_events = await self.collection.count_documents(query)
            cursor = self.collection.find(query, projection)
            cursor.sort("start_datetime", 1).skip(skip).limit(events_per_page)

            events = await cursor.to_list(length=events_per_page)

            response = {
                "events": events,
                "total_events": total_events,
                "current_page": page,
                "total_pages": (total_events + events_per_page - 1) // events_per_page,
                "events_per_page": events_per_page,
            }

            serialized_response = json.loads(json.dumps(response, cls=JSONEncoder))
            return serialized_response
        except Exception as e:
            self.logger.error(f"Database error while fetching events: {str(e)}")
            raise

    async def add_attendance(self, event_id: str, attendances: List[AttendanceRecord]):
        attendance_records = [
            {
                "event_id": ObjectId(event_id),
                "user_id": attendance.user_id,
                "status": attendance.status.value,  # Use .value to get the string representation
                "timestamp": datetime.now(),
            }
            for attendance in attendances
        ]

        try:
            result = await self.attendance_collection.insert_many(attendance_records)
            if result.inserted_ids:
                invalidate_caches.delay([f"attendances_{event_id}"])
                return result.inserted_ids
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to insert attendance records: {str(e)}"
            )

    async def get_attendances_by_event_id(
        self,
        event_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        cache_key = f"attendances_{event_id}_{fields}_{limit}_{cursor}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        projection = {field: 1 for field in fields} if fields else None
        if projection:
            projection["_id"] = 1  # Always include _id for cursor-based pagination

        query = {"event_id": ObjectId(event_id)}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        attendances = (
            await self.attendance_collection.find(query, projection=projection)
            .sort("_id", 1)
            .limit(limit + 1)
            .to_list(None)
        )

        has_next = len(attendances) > limit
        if has_next:
            attendances = attendances[:-1]

        result = {
            "attendances": attendances,
            "has_next": has_next,
            "next_cursor": str(attendances[-1]["_id"]) if has_next else None,
        }

        # Convert ObjectIds to strings for JSON serialization
        for attendance in result["attendances"]:
            attendance["_id"] = str(attendance["_id"])
            attendance["event_id"] = str(attendance["event_id"])

        serialized_result = dumps(result)
        await self.redis_client.set(cache_key, serialized_result, expire=60)
        return result

    async def get_events(self, params: ListEventParams) -> ListEventResponseSchema:
        try:
            pipeline = self._build_pipeline(params)
            logger.debug(f"MongoDB Aggregation Pipeline: {pipeline}")

            result = await self.collection.aggregate(pipeline).to_list(length=None)
            logger.debug(f"Aggregation Result: {result}")

            if not result:
                logger.warning(f"No events found for params: {params}")
                return ListEventResponseSchema(
                    events=[],
                    total_count=0,
                    page=params.page,
                    page_size=params.page_size,
                    total_pages=0,
                )

            events = result[0]["events"]
            total_count = result[0]["total_count"]
            total_pages = -(-total_count // params.page_size)  # Ceiling division

            logger.info(f"Found {total_count} events for params: {params}")

            return ListEventResponseSchema(
                events=events,
                total_count=total_count,
                page=params.page,
                page_size=params.page_size,
                total_pages=total_pages,
            )
        except Exception as e:
            logger.error(f"Error in get_events: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

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

    async def update_attendance(
        self, new_attendances: List[AttendanceRecord], event_id: str
    ):

        # Prepare bulk write operations
        bulk_operations = []
        for attendance in new_attendances:
            attendance_id = ObjectId(attendance.id)
            new_status = attendance.status

            bulk_operations.append(
                UpdateOne(
                    {"_id": attendance_id},
                    {"$set": {"status": new_status}},
                    upsert=False,  # We don't want to create new documents, only update existing ones
                )
            )

        # Perform bulk write operation
        if bulk_operations:
            result = await self.attendance_collection.bulk_write(bulk_operations)

        # Clear cache
        invalidate_caches.delay([f"attendances_{event_id}"])

        status = "success" if result and result.modified_count > 0 else "failure"
        # Create and return the EventResponseSchema
        return EventResponseSchema(event_id=event_id, status=status)

    async def create_private_lesson(self, lesson_data: dict):
        collection = await self.private_lesson_collection
        result = await collection.insert_one(lesson_data)
        invalidate_caches.delay(
            [
                f"private_lesson_{lesson_request.player_id}_player_id",
                f"private_lesson_{lesson_request.coach_id}_coach_id",
            ]
        )
        return await collection.find_one({"_id": result.inserted_id})

    async def create_private_lesson_request(
        self, lesson_request: CreatePrivateLessonSchema
    ):
        lesson_request_data = lesson_request.dict()
        lesson_request_data["request_status"] = RequestStatus.PENDING
        lesson_request_data["request_date"] = datetime.utcnow()
        lesson_request_data["response_date"] = None
        lesson_request_data["response_notes"] = None

        collection = await self.private_lesson_collection
        created_request = await collection.insert_one(lesson_request_data)

        return created_request.inserted_id

    async def approve_private_lesson_request(self, lesson_id: str, update_data: dict):
        try:
            collection = await self.private_lesson_collection
            updated_request = await collection.update_one(
                {"_id": ObjectId(lesson_id)}, {"$set": update_data}
            )

            if updated_request.modified_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No documents were modified. Update failed.",
                )

            return updated_request.modified_count

        except Exception as e:
            print(f"Error in approve_private_lesson_request: {str(e)}")
            raise e

    async def get_private_lesson_by_user_id(self, id: str, field: str):
        collection = await self.private_lesson_collection
        query = {field: id}
        cursor = collection.find(query)
        result = await cursor.to_list(length=None)
        return result
