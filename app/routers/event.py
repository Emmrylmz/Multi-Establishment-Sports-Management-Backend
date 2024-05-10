from fastapi import APIRouter, status, Depends, HTTPException, Request
from typing import List
from ..controller.EventController import EventController
from pydantic import BaseModel
from ..models.event_schemas import CreateEventSchema
from ..oauth2 import require_user
from bson import ObjectId

event_controller = EventController()

router = APIRouter()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    payload: CreateEventSchema,
    request: Request,
    user: dict = Depends(require_user),
    response_model=CreateEventSchema,
):
    return await EventController.create_event(payload, request, user)


@router.get("/{event_id}", response_model=CreateEventSchema)
async def get_event(event_id: str):
    return await EventController.read_event(event_id)


@router.delete("/delete/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str):
    return await EventController.delete_event(event_id)


@router.post("/list")
def list_events(query: dict):
    return EventController.list_events(query)


@router.post("/update/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_event(event_id: str, payload: CreateEventSchema):
    return await EventController.update_event(event_id, payload)


# , user: dict = Depends(require_user)
