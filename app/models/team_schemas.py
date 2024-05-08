from pydantic import BaseModel, Field
from typing import List
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


class CreateTeamSchema(BaseModel):
    team_id: str = Field(..., example="team123")
    team_name: str = Field(..., example="Warriors")
    team_players: List[str] = Field(..., example=["player1", "player2"])
    team_coaches: List[str] = Field(..., example=["coach1", "coach2"])

    class Config:
        orm_mode = True
        fields = {"id": "_id"}
