from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Literal, List
from bson.objectid import ObjectId
import struct
import pydantic
from enum import Enum


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


class EventType(str, Enum):
    GAME = "game"
    PRIVATE_LESSON = "private_lesson"
    TRAINING = "training"


class CreateEventSchema(BaseModel):
    event_type: EventType
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
    team_ids: List[str]


class UpdateEventSchema(BaseModel):
    event_date: Optional[datetime]  # corrected from event_data
    place: Optional[str]
    event_type: Optional[EventType]
    description: Optional[str]


class EventResponseSchema(BaseModel):
    event_id: str
    status: str


class Event(BaseModel):
    event_type: EventType
    place: str
    event_date: datetime  # corrected from event_data
    description: str


class ListEventResponseSchema(BaseModel):
    team_name: str
    events: List[Event]


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CreatePrivateLessonSchema(BaseModel):
    # id: Optional[PyObjectId] = Field(alias="_id")
    place: Optional[str]
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    description: Optional[str]
    player_id: Optional[str]
    lesson_fee: Optional[float]
    paid: bool = False
    coach_id: Optional[str]

    # New fields for request ticket
    request_status: RequestStatus = RequestStatus.PENDING
    request_date: datetime = Field(default_factory=datetime.utcnow)
    preferred_date: Optional[datetime]
    preferred_time: Optional[str]
    request_notes: Optional[str]
    response_date: Optional[datetime]
    response_notes: Optional[str]

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PrivateLessonResponseSchema(BaseModel):
    lesson_id: str
    status: str
