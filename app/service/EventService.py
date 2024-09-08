from bson import ObjectId
from pymongo.collection import Collection
from datetime import datetime
from app.serializers.eventSerializers import eventEntity
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
from bson.json_util import dumps, loads
from typing import Optional
from app.celery_app.celery_tasks import invalidate_caches
from redis.exceptions import RedisError
import json
from app.utils import JSONEncoder, logging
from ..repositories.EventRepository import EventRepository
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


class EventService:
    @classmethod
    async def initialize(
        cls, event_repository: EventRepository, redis_client: RedisClient
    ):
        self = cls.__new__(cls)
        await self.__init__(redis_client, event_repository)
        return self

    async def __init__(
        self, redis_client: RedisClient, event_repository: EventRepository
    ):
        self.event_repository = event_repository
        self.redis_client = redis_client

    async def get_private_lesson_by_id(self, private_lesson_id: str):
        return await self.event_repository.get_private_lesson_by_id(private_lesson_id)

    async def get_event_by_id(self, event_id: str):
        return await self.event_repository.get_event_by_id(event_id)

    async def get_all_events_by_team_id(
        self,
        team_object_ids: List[ObjectId],
        page: int,
        events_per_page: int = 10,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        skip = (page - 1) * events_per_page
        projection = {field: 1 for field in fields} if fields else None

        total_events, events = await self.event_repository.get_event_by_team_ids(
            team_object_ids, skip=skip, limit=events_per_page, projection=projection
        )

        response = {
            "events": events,
            "total_events": total_events,
            "current_page": page,
            "total_pages": (total_events + events_per_page - 1) // events_per_page,
            "events_per_page": events_per_page,
        }
        return json.loads(json.dumps(response, cls=JSONEncoder))

    async def add_attendance(self, event_id: str, attendances: List[AttendanceRecord]):
        attendance_records = [
            {
                "event_id": ObjectId(event_id),
                "user_id": attendance.user_id,
                "status": attendance.status.value,
                "timestamp": datetime.now(),
            }
            for attendance in attendances
        ]

        result = await self.event_repository.insert_attendances(attendance_records)
        if result.inserted_ids:

            invalidate_caches.delay([f"attendances_{event_id}"])

            return result.inserted_ids

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
            return json.loads(cached_result)

        query = {"event_id": ObjectId(event_id)}
        if cursor:
            query["_id"] = {"$gt": ObjectId(cursor)}

        projection = {field: 1 for field in fields} if fields else None
        attendances = await self.event_repository.get_attendances_by_event_id(
            event_id, query, projection=projection, limit=limit
        )

        result = {
            "attendances": attendances,
            "has_next": len(attendances) > limit,
            "next_cursor": (
                str(attendances[-1]["_id"]) if len(attendances) > limit else None
            ),
        }

        await self.redis_client.set(
            cache_key, json.dumps(result, cls=JSONEncoder), expire=60
        )
        return result

    async def get_events(self, params: ListEventParams) -> ListEventResponseSchema:
        try:
            result = await self.event_repository.get_events_for_teams(params)

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

    async def update_attendance(
        self, new_attendances: List[AttendanceRecord], event_id: str
    ):
        bulk_operations = [
            UpdateOne(
                {"_id": ObjectId(attendance.id)},
                {"$set": {"status": attendance.status.value}},
                upsert=False,
            )
            for attendance in new_attendances
        ]

        if bulk_operations:
            result = await self.event_repository.bulk_update_attendance(bulk_operations)

            invalidate_caches.delay([f"attendances_{event_id}"])

            status = "success" if result.modified_count > 0 else "failure"
            return EventResponseSchema(event_id=event_id, status=status)

    async def create_private_lesson(self, lesson_data: dict):
        lesson_id = await self.event_repository.insert_private_lesson(lesson_data)

        invalidate_caches.delay(
            [
                f"private_lesson_{lesson_data['player_id']}_player_id",
                f"private_lesson_{lesson_data['coach_id']}_coach_id",
            ]
        )

        return lesson_id

    async def create_private_lesson_request(
        self, lesson_request: CreatePrivateLessonSchema
    ):
        lesson_request_data = lesson_request.dict()
        lesson_request_data["request_status"] = RequestStatus.PENDING
        lesson_request_data["request_date"] = datetime.utcnow()
        lesson_request_data["response_date"] = None
        lesson_request_data["response_notes"] = None

        return await self.event_repository.insert_private_lesson(lesson_request_data)

    async def approve_private_lesson_request(self, lesson_id: str, update_data: dict):
        updated_count = await self.event_repository.update_private_lesson(
            lesson_id, update_data
        )
        if updated_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update failed.",
            )
        return updated_count

    async def get_private_lesson_by_user_id(self, id: str, field: str):
        return await self.event_repository.get_private_lessons_by_user(id, field)
