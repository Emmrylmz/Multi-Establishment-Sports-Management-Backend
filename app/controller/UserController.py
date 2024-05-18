from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from ..models.user_schemas import UserAttributesSchema
from bson import ObjectId
from .BaseController import BaseController


class UserController(BaseController):
    async def update_user_information(
        self,
        payload: UserAttributesSchema,
        user,
    ):
        user_id = self.format_handler(user["_id"])
        payload_dict = payload.dict()
        print(payload_dict)
        on_boarding = payload_dict["on_boarding"]
        payload_dict["_id"] = user_id
        if on_boarding:
            res = await self.user_service.create(payload_dict)
            return res
        else:
            res = await self.user_service.update(user_id, payload_dict)
            return res
