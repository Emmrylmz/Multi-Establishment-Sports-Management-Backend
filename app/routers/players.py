from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from typing import Optional
from pydantic import BaseModel
import requests
import librosa
import json
import numpy as np
import io
from data.models.player import Player
from fastapi import HTTPException
from datetime import datetime, timedelta

# DATABASE DEPENDENCIES
from database.config.database import players
from database.models.player_model import Player
from database.scheme.schemes import individual_serial_Players, list_serial_Players
from bson import ObjectId

# Router provider to modularize the routers. This router will only be for Audio Routes
router = APIRouter()

@router.get("/api/players", tags=["players"])
async def getAllPlayersInfo():
    data = players.find()
    return list_serial_Players(data)

@router.get("/api/players/{player_id}", tags=["players"])
async def getPlayerInfo(player_id: str):
    data = players.find_one({"_id": ObjectId(player_id)})
    
    if data:
        return individual_serial_Players(data)
    else:
        raise HTTPException(status_code=404, detail="Player not found")
    
@router.post("/api/players", tags=["players"])
async def createPlayer(player: Player):
    player = Player(**player.model_dump())
    player.save()
    return player.model_dump()
