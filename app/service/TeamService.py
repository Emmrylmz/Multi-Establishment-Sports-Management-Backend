from motor.motor_asyncio import (
    AsyncIOMotorDatabase,
    AsyncIOMotorClientSession,
)
from fastapi import Depends, HTTPException, status
from .MongoDBService import MongoDBService
from ..utils import ensure_object_id
from pymongo.errors import PyMongoError
from bson import ObjectId
from typing import List, Dict, Any, Optional
from aiocache import cached
from aiocache.serializers import PickleSerializer
from ..redis_client import RedisClient
from ..models.user_schemas import UserRole
from app.celery_app.celery_tasks import invalidate_caches
import json
from ..repositories.TeamRepository import TeamRepository


class TeamService:
    @classmethod
    async def initialize(
        cls, team_repository: TeamRepository, redis_client: RedisClient
    ):
        self = cls.__new__(cls)
        await self.__init__(team_repository, redis_client)
        return self

    async def __init__(
        self, team_repository: TeamRepository, redis_client: RedisClient
    ):
        self.team_repository = team_repository
        self.redis_client = redis_client

    async def add_user_to_teams(
        self, user_id: ObjectId, team_ids: List[str], user_role_field: str, session=None
    ):
        result = await self.team_repository.add_user_to_teams(
            user_id, team_ids, user_role_field, session
        )
        if result.matched_count == 0:
            # No teams were found, raise an exception to stop the transaction
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No teams found with the provided IDs",
            )
        return result.modified_count

    async def get_team_users_by_id(
        self, team_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        cache_key = f"team_users:{team_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        results = await self.team_repository.get_team_users_by_id(team_id)
        team_data = results[0] if results else {"player_infos": [], "coach_infos": []}
        await self.redis_client.set(cache_key, team_data, expire=300)
        return team_data

    async def get_teams_by_id(self, team_ids: List[str]):
        cache_key = f"teams_by_id:{','.join(map(str, team_ids))}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        team_object_ids = [ObjectId(tid) for tid in team_ids]
        teams = await self.team_repository.get_teams_by_id(team_object_ids)
        await self.redis_client.set(cache_key, teams, expire=300)
        return teams

    async def get_all_teams(self, cursor: Optional[str] = None, limit: int = 20):
        cache_key = f"all_teams:{cursor}:{limit}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        teams = await self.team_repository.get_all_teams(cursor, limit)
        has_more = len(teams) > limit
        if has_more:
            teams = teams[:limit]

        result = {
            "teams": [
                {"id": str(team["_id"]), "name": team["team_name"]} for team in teams
            ],
            "has_more": has_more,
            "next_cursor": str(teams[-1]["_id"]) if has_more else None,
        }
        await self.redis_client.set(cache_key, result, expire=300)
        return result

    async def get_all_teams_by_province(
        self, province: str, cursor: Optional[str] = None, limit: int = 20
    ):
        cache_key = f"teams_by_province:{province}:{cursor}:{limit}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        teams = await self.team_repository.get_all_teams_by_province(
            province, cursor, limit
        )
        has_more = len(teams) > limit
        if has_more:
            teams = teams[:limit]

        result = {
            "teams": [
                {"id": str(team["_id"]), "name": team["team_name"]} for team in teams
            ],
            "has_more": has_more,
            "next_cursor": str(teams[-1]["_id"]) if has_more else None,
        }
        await self.redis_client.set(cache_key, result, expire=300)
        return result

    async def get_team_coaches(self, team_ids: List[str]):
        cache_key = f"team_coaches:{','.join(team_ids)}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)  # Deserialize the cached data

        team_object_ids = [ObjectId(tid) for tid in team_ids]
        try:
            result = await self.team_repository.get_team_coaches(team_object_ids)
            if result and isinstance(result, list) and len(result) > 0:
                if "team_coaches" in result[0]:
                    coaches = result[0]["team_coaches"]
                else:
                    return []
            else:
                return []

            # Serialize coaches to JSON string
            coaches_json = json.dumps(coaches)

            # Cache the serialized data
            await self.redis_client.set(cache_key, coaches_json, expire=300)

            return coaches
        except Exception as e:
            logging.exception(f"An error occurred while fetching coaches: {str(e)}")
            return []

    async def get_all_coaches_by_province(
        self, province: str, cursor: Optional[str] = None, limit: int = 20
    ):
        cache_key = f"coaches_by_province:{province}:{cursor}:{limit}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return cached_data

        coaches = await self.team_repository.get_all_coaches_by_province(
            province, cursor, limit
        )
        has_more = len(coaches) > limit
        if has_more:
            coaches = coaches[:limit]

        result = {
            "coaches": [
                {"id": str(coach["_id"]), "name": coach["name"]} for coach in coaches
            ],
            "has_more": has_more,
            "next_cursor": str(coaches[-1]["_id"]) if has_more else None,
        }
        await self.redis_client.set(cache_key, result, expire=300)
        return result

    async def remove_user_from_teams(
        self,
        user_id: ObjectId,
        team_ids: List[str],
        session: Optional[AsyncIOMotorClientSession] = None,
    ):
        team_object_ids = [ObjectId(team_id) for team_id in team_ids]
        try:
            result = await self.team_repository.remove_user_from_teams(
                user_id, team_object_ids, session
            )
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No matching teams found or user not in teams",
                )
            invalidate_caches.delay(team_ids)
            return {"modified_count": result.modified_count}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    async def get_unique_provinces(self):
        provinces = await self.team_repository.get_unique_provinces()
        return provinces

    async def get_all_team_ids_by_province(self, province: str, session=None):
        team_ids = await self.team_repository.get_all_team_ids_by_province(
            province, session
        )
        return team_ids
