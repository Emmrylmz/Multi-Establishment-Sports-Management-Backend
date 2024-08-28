from fastapi import Depends, Query
from pydantic import ValidationError
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from ..service.MongoDBService import MongoDBService
from ..database import get_collection
from typing import List
from ..models.note_schemas import NoteType, NoteInDB, NoteCreate, NoteResponse
from ..redis_client import RedisClient


class NoteService(MongoDBService):
    @classmethod
    async def initialize(
        cls, database: AsyncIOMotorDatabase, redis_client: RedisClient
    ):
        self = cls.__new__(cls)
        await self.__init__(database, redis_client)
        return self

    async def __init__(self, database: AsyncIOMotorDatabase, redis_client: RedisClient):
        self.database = database
        self.redis_client = redis_client
        self.collection = await get_collection("Note", database)
        await super().__init__(self.collection)

    async def create_note(self, payload: NoteCreate) -> NoteResponse:
        # Validate the payload based on note_type
        try:
            self.validate_note_payload(payload)
        except ValidationError as e:
            raise ValueError(f"Invalid payload for note type : {str(e)}")

        # Create the note document
        note_data = payload.dict()  # Convert the entire payload to a dictionary
        note_data["author_id"] = (
            "placeholder"  # You might want to get this from the current user
        )
        note_data["created_at"] = datetime.utcnow()

        # Create the note
        result = await self.create(note_data)

        # Construct the NoteInDB object
        note_in_db = NoteInDB(id=str(result["_id"]), **note_data)

        # Convert to NoteResponse
        return NoteResponse(**note_in_db.dict())

    def validate_note_payload(self, payload: NoteCreate):
        note_type = payload.note_type
        if note_type == NoteType.INDIVIDUAL:
            if not payload.recipient_id:
                raise ValueError("recipient_id is required for individual notes")
        elif note_type == NoteType.TEAM:
            if not payload.team_id:
                raise ValueError("team_id is required for team notes")
        elif note_type == NoteType.PROVINCE:
            if not payload.province_id:
                raise ValueError("province_id is required for province notes")
        elif note_type == NoteType.GLOBAL:
            # No additional fields required for global notes
            pass
        else:
            raise ValueError(f"Unknown note type: {note_type}")

        # Ensure that only the relevant field is set based on the note type
