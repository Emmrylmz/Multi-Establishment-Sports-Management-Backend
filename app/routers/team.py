from fastapi import APIRouter, status, Depends, HTTPException
from typing import List
from ..controller.EventController import EventController
from pydantic import BaseModel
from ..models.event_schemas import CreateEventSchema
from ..oauth2 import require_user
from ..service.EventService import EventService
from bson import ObjectId
