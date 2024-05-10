from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from bson.objectid import ObjectId
import struct
import pydantic


class BeeObjectId(ObjectId):
    # fix for FastApi/docs
    __origin__ = pydantic.typing.Literal
    __args__ = (str,)


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
        json_encoders = {datetime: lambda dt: dt.isoformat()}
        schema_extra = {
            "event_type": "Game",
            "creator_id": "creator123",
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
