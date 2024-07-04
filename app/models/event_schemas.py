from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Literal, List
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
    start_datetime: datetime  # Combined start date and time
    end_datetime: datetime  # Combined end date and time
    created_at: datetime
    team_id: str
    description: str
    creator_id: str

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

    @validator("end_datetime")
    def check_dates(cls, v, values):
        if "start_datetime" in values and v <= values["start_datetime"]:
            raise ValueError("end_datetime must be after start_datetime")
        return v


class ListTeamEventSchema(BaseModel):
    team_id: List[str]


class UpdateEventSchema(BaseModel):
    event_date: Optional[datetime]  # corrected from event_data
    place: Optional[str]
    event_type: Optional[str]
    description: Optional[str]


class EventResponseSchema(BaseModel):
    event_id: str
    status: str


class Event(BaseModel):
    event_type: str
    place: str
    event_date: datetime  # corrected from event_data
    description: str


class ListEventResponseSchema(BaseModel):
    team_name: str
    events: List[Event]
