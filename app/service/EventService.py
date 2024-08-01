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
from ..models.event_schemas import CreatePrivateLessonSchema, RequestStatus
from ..models.attendance_schemas import AttendanceFormSchema
from ..redis_client import RedisClient
from ..database import get_database, get_collection
from bson.json_util import dumps, loads
from typing import Optional


class EventService(MongoDBService):
    @classmethod
    async def create(cls, database: AsyncIOMotorDatabase, redis_client: RedisClient):
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

    async def get_all_events_by_team_id(
        self,
        team_object_ids: List[ObjectId],
        skip: int = 0,
        limit: int = 20,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        cache_key = f"all_events_{team_object_ids}_{skip}_{limit}_{fields}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        projection = {field: 1 for field in fields} if fields else None
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
                    "events": {"$push": "$$ROOT"},
                }
            },
            {"$project": {"_id": 0, "team_id": "$_id", "team_name": 1, "events": 1}},
            {"$skip": skip},
            {"$limit": limit},
        ]

        if projection:
            pipeline.append({"$project": projection})

        results = await self.collection.aggregate(pipeline).to_list(length=None)
        await self.redis_client.set(cache_key, dumps(results), expire=300)
        return results

    async def add_attendance(self, event_id: str, attendances: List[Dict[str, Any]]):
        attendance_records = [
            {
                "event_id": ObjectId(event_id),
                "user_id": attendance["user_id"],
                "status": attendance["status"],
                "timestamp": datetime.now(),
            }
            for attendance in attendances
        ]

        try:
            result = await self.attendance_collection.insert_many(attendance_records)
            await self.redis_client.delete(f"attendances_{event_id}")
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

    async def get_upcoming_events(
        self,
        team_ids: List[str],
        skip: int = 0,
        limit: int = 20,
        fields: Optional[List[str]] = None,
    ):
        cache_key = f"upcoming_events_{team_ids}_{skip}_{limit}_{fields}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        try:
            team_object_ids = [ObjectId(team_id) for team_id in team_ids]
            projection = {field: 1 for field in fields} if fields else None

            pipeline = [
                {
                    "$match": {
                        "team_id": {"$in": team_object_ids},
                        "start_datetime": {"$gt": datetime.utcnow()},
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
                        "events": {"$push": "$$ROOT"},
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
                {"$skip": skip},
                {"$limit": limit},
            ]

            if projection:
                pipeline.append({"$project": projection})

            result = await self.collection.aggregate(pipeline).to_list(length=None)
            await self.redis_client.set(cache_key, dumps(result), expire=300)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_attendance(self, event_id: str, event_type: str, new_attendances):
        event_object_id = ObjectId(event_id)

        event = await self.collection.find_one({"_id": event_object_id})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        existing_attendances = await self.attendance_collection.find(
            {"event_id": event_object_id}
        ).to_list(None)

        existing_attendances_dict = {
            str(att["user_id"]): att["status"] for att in existing_attendances
        }

        attendance_updates = []

        for attendance in new_attendances:
            user_id = attendance.user_id
            new_status = attendance.status

            attendance_updates.append(
                UpdateOne(
                    {"event_id": event_object_id, "user_id": user_id},
                    {"$set": {"status": new_status}},
                    upsert=True,
                )
            )

        await self.redis_client.delete(f"attendances_{event_id}")

        return {"message": "Attendance records updated successfully"}

    async def create_private_lesson(self, lesson_data: dict):
        collection = await self.private_lesson_collection
        result = await collection.insert_one(lesson_data)
        await self.redis_client.delete(
            f"private_lesson_{lesson_data['player_id']}_player_id"
        )
        await self.redis_client.delete(
            f"private_lesson_{lesson_data['coach_id']}_coach_id"
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
        await self.redis_client.delete(
            f"private_lesson_{lesson_request.player_id}_player_id"
        )
        await self.redis_client.delete(
            f"private_lesson_{lesson_request.coach_id}_coach_id"
        )
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

            lesson = await collection.find_one({"_id": ObjectId(lesson_id)})
            if lesson:
                await self.redis_client.delete(
                    f"private_lesson_{lesson['player_id']}_player_id"
                )
                await self.redis_client.delete(
                    f"private_lesson_{lesson['coach_id']}_coach_id"
                )

            return updated_request.modified_count
        except Exception as e:
            print(f"Error in approve_private_lesson_request: {str(e)}")
            raise e

    async def get_private_lesson_by_user_id(self, id: str, field: str):
        cache_key = f"private_lesson_{id}_{field}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return cached_result

        collection = await self.private_lesson_collection
        query = {field: id}
        cursor = collection.find(query)
        result = await cursor.to_list(length=None)
        await self.redis_client.set(cache_key, dumps(result), expire=300)
        return result
