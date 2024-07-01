from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from ..models.user_schemas import UserAttributesSchema
from bson import ObjectId
from .BaseController import BaseController
from ..oauth2 import require_user


class UserController(BaseController):
    async def update_user_information(
        self,
        payload: UserAttributesSchema,
        user_id: str = Depends(require_user),
    ):
        user_id = self.format_handler(user_id)
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
