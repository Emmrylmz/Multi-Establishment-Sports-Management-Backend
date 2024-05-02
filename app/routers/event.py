from fastapi import APIRouter, status, Depends, HTTPException
from typing import List
from ..controller.EventController import EventController
from pydantic import BaseModel
from ..models.event_schemas import CreateEventSchema
from ..oauth2 import require_user
from ..service.EventService import EventService
from bson import ObjectId


event_controller = EventController()

router = APIRouter()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
)
async def create_event(payload: CreateEventSchema, user: dict = Depends(require_user)):
    return await EventController.create_event(payload, user)


@router.get("/{event_id}", response_model=CreateEventSchema)
async def get_event(event_id: str):
    return await EventController.read_event(event_id)


@router.delete("/delete/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str):
    return await EventController.delete_event(event_id)


@router.post("/list", response_model=List[CreateEventSchema])
async def list_events(team_id: str):
    return EventService.list_events(team_id)


@router.post("/update/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_event(event_id: str, payload: CreateEventSchema):
    return await EventController.update_event(event_id, payload)


# , user: dict = Depends(require_user)
