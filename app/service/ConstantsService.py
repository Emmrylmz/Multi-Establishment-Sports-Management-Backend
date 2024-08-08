from fastapi import Depends, status, HTTPException
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from ..database import get_collection
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from ..service.MongoDBService import MongoDBService
from ..models.constant_schemas import (
    ConstantCreate,
    ConstantUpdate,
    ConstantResponse,
)
from typing import List, Optional
from ..redis_client import RedisClient


class ConstantsService(MongoDBService):
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
        self.collection = await get_collection("Constant", database)
        await super().__init__(self.collection)

    async def create_constant(self, constant: ConstantCreate) -> ConstantResponse:
        now = datetime.utcnow()
        constant_dict = constant.dict()
        constant_dict.update({"created_at": now, "updated_at": now})

        result = await self.collection.insert_one(constant_dict)

        if result.inserted_id:

            return ConstantResponse(
                id=str(result.inserted_id),
                status="success" if result.inserted_id else "failed",
                **constant_dict
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create constant",
            )

    async def update_constant(
        self, constant_id: str, constant: ConstantUpdate
    ) -> ConstantResponse:
        now = datetime.utcnow()
        update_data = constant.dict()
        update_data["updated_at"] = now
        result = await self.collection.update_one(
            {"_id": ObjectId(constant_id)}, {"$set": update_data}
        )
        if result.modified_count:

            return ConstantResponse(
                id=str(constant_id),
                status="success" if result.modified_count > 0 else "failed",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Constant not found"
            )

    async def get_all_constants(self) -> List[ConstantCreate]:
        cursor = self.collection.find()
        constants = await cursor.to_list(length=None)
        return [ConstantCreate(**constant) for constant in constants]

    async def get_constant(self, constant_id: str) -> ConstantCreate:
        constant = await self.collection.find_one({"_id": ObjectId(constant_id)})
        if constant:
            return ConstantCreate(**constant)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Constant not found"
            )

    async def delete_constant(self, constant_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(constant_id)})
        if result.deleted_count:
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Constant not found"
            )

    async def get_constant_by_key(self, key: str) -> Optional[ConstantResponse]:
        constant = await self.collection.find_one({"key": key})
        if constant:
            return ConstantResponse(id=str(constant["_id"]), **constant)
        return None
