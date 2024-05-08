from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from bson.objectid import ObjectId as BsonObjectId


class PydanticObjectId(BsonObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, BsonObjectId):
            raise TypeError("ObjectId required")
        return str(v)


class PushTokenSchema(BaseModel):
    token: str
    _id: PydanticObjectId

    class Config:
        orm_mode = True
        json_encoders = {BsonObjectId: lambda v: str(v)}
