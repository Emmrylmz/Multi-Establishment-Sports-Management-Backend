from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from bson.objectid import ObjectId
import struct
import pydantic


class BeeObjectId(ObjectId):
    # fix for FastApi/docs
<<<<<<< HEAD
    __origin__ = pydantic.typing.Literal
    __args__ = (str,)
=======
    _origin_ = pydantic.typing.Literal
    _args_ = (str,)
>>>>>>> rabbit_stann


pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str
pydantic.json.ENCODERS_BY_TYPE[BeeObjectId] = str


class CreateEventSchema(BaseModel):
    event_type: Literal["Game", "Training"]
    creator_id: str
    place: str
    event_date: datetime  # corrected from event_data
    created_at: datetime = Field(default_factory=datetime.now)
    team_id: str
    description: Optional[str]

    class Config:
        orm_mode = True
        fields = {"id": "_id"}


class CreateGameEventSchema(CreateEventSchema):
    opponent: str