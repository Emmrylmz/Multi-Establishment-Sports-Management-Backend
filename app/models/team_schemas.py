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
    team_name: str = Field(..., example="Warriors")
    team_players: List[str] = Field(..., example=["player1", "player2"])
    team_coaches: List[str] = Field(..., example=["coach1", "coach2"])
    province: str = Field(..., example="Izmir")

    class Config:
        orm_mode = True
        fields = {"id": "_id"}


class PlayerTokenRequest(BaseModel):
    team_id: str

    class Config:
        orm_mode = True
        fields = {"id": "_id"}


class UserInsert(BaseModel):
    team_ids: List[str]
    user_ids: List[str]

    class Config:
        orm_mode = True
        fields = {"id": "_id"}


class TeamPlayers(BaseModel):
    team_id: str


class TeamQueryById(BaseModel):
    team_ids: List[str]
