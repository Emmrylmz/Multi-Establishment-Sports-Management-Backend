from fastapi import APIRouter, status, Depends, HTTPException, Request
from typing import List
from ..controller.EventController import EventController
from pydantic import BaseModel
from ..models.event_schemas import CreateEventSchema
from ..oauth2 import require_user
from bson import ObjectId

event_controller = EventController()

router = APIRouter()


<<<<<<< HEAD
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
=======
@router.post("/create", response_model=CreateEventSchema, status_code=status.HTTP_201_CREATED)
async def create_event(payload: CreateEventSchema, request: Request, user: dict = Depends(require_user)):
>>>>>>> rabbit_stann
    return await EventController.create_event(payload, request, user)

@router.post("/update/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_event(event_id: str, payload: CreateEventSchema, request: Request):
    return await EventController.update_event(event_id, payload, request)

@router.delete("/delete/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str, request: Request):
    return await EventController.delete_event(event_id, request)



@router.get("/{event_id}", response_model=CreateEventSchema)
async def get_event(event_id: str):
    return await EventController.read_event(event_id)

<<<<<<< HEAD

@router.delete("/delete/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str):
    return await EventController.delete_event(event_id)


@router.post("/list")
def list_events(query: dict):
    return EventController.list_events(query)


@router.post("/update/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_event(event_id: str, payload: CreateEventSchema):
    return await EventController.update_event(event_id, payload)
=======
@router.post("/list", response_model=List[CreateEventSchema])
async def list_events(team_id: str):
    return await EventService.list_events(team_id)
>>>>>>> rabbit_stann


# , user: dict = Depends(require_user)
