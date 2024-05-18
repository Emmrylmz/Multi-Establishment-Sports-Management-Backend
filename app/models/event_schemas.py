from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from bson.objectid import ObjectId
import struct
import pydantic


class BeeObjectId(ObjectId):
    # fix for FastApi/docs
    _origin_ = pydantic.typing.Literal
    _args_ = str


pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str
pydantic.json.ENCODERS_BY_TYPE[BeeObjectId] = str
pydantic.json.ENCODERS_BY_TYPE[datetime] = str


class CreateEventSchema(BaseModel):
    event_type: str
    place: str
    event_date: datetime  # corrected from event_data
    created_at: datetime
    team_id: str
    description: str

    class Config:
        orm_mode = True
        json_encoders = {ObjectId: lambda o: str(o), datetime: lambda o: o.isoformat()}
        schema_extra = {
            "event_type": "Game",
            "place": "Stadium XYZ",
            "event_date": "2023-05-10T15:00:00",
            "created_at": "2023-05-01T12:34:56",
            "team_id": "team456",
            "description": "Annual championship game",
        }

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, _id: str):
        self._id = _id


class ListTeamEventSchema(BaseModel):
    team_id: str
