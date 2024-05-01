from fastapi import APIRouter, status, Depends
from typing import List
from ..controller.EventController import EventController
from pydantic import BaseModel
from ..models.event_schemas import CreateEventSchema
from ..oauth2 import require_user
from ..service.EventService import EventService
from ..models.event_schemas import CreateEventSchema


event_controller = EventController()

router = APIRouter()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
)
async def create_event(payload: CreateEventSchema):
    return await EventController.create_event(payload)


@router.get("/{event_id}", response_model=CreateEventSchema)
# def read_event()


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str, user: dict = Depends(require_user)):
    if not EventService.delete_event(ObjectId(event_id)):
        raise HTTPException(status_code=404, detail="Event not found")
        return {"message": "Event deleted successfully"}


@router.get("/", response_model=List[CreateEventSchema])
async def list_events(user: dict = Depends(require_user)):
    events = EventService.list_events()
    return events
