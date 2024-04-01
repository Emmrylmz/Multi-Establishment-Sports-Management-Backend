from pydantic import BaseModel, Field
from typing import Optional
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import Optional
from database.config.database import players

class Player(BaseModel):
    id: Optional[str] = Field(None, alias='_id')
    playerName: str
    playerAge: int
    playerHeight: float
    playerWeight: float

    def save(self):
        player_data = self.model_dump()
        players.insert_one(player_data)

    @classmethod
    def get(cls, player_id: str):
        player_data = players.find_one({'_id': player_id})
        if player_data:
            return cls(**player_data)

    @classmethod
    def update(cls, player_id: str, data: dict):
        players.update_one({'_id': player_id}, {'$set': data})

    @classmethod
    def delete(cls, player_id: str):
        players.delete_one({'_id': player_id})