from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from ..models.user_schemas import UserAttributesSchema
from bson import ObjectId
from ..oauth2 import require_user
from ..service import UserService


class UserController:
    @classmethod
    async def create(
        cls,
        user_service: UserService,
    ):
        self = cls.__new__(cls)
        await self.__init__(user_service)
        return self

    def __init__(
        self,
        user_service: UserService,
    ):
        self.user_service = user_service

    async def update_user_information(
        self,
        payload: UserAttributesSchema,
        user_id: str = Depends(require_user),
    ):
        user_id = ObjectId(user_id)
        payload_dict = payload.dict()
        print(payload_dict)
        on_boarding = payload_dict.pop("on_boarding", None)

        if on_boarding is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The on_boarding field is required.",
            )

        payload_dict["_id"] = user_id

        if on_boarding:
            res = await self.user_service.create(payload_dict)
        else:
            res = await self.user_service.update(user_id, payload_dict)

        return res

    async def get_user_information(self, user_id: str):
        return await self.user_service.get_by_id(user_id)

    async def get_all_users_by_province(self, province: str = None):
        return await self.user_service.get_by_province(province)

    async def search_users_by_name(self, query: str):
        return await self.user_service.search_users_by_name(query)

    async def get_users(self, limit: int = 100):
        users = (
            await self.user_service.collection.find().limit(limit).to_list(length=limit)
        )
        return users
