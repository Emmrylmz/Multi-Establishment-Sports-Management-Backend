from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from ..tools.RabbitClient import RabbitClient
from ..database import Event
from app.service.EventService import EventService
from ..oauth2 import require_user
from ..models.event_schemas import CreateEventSchema
from bson import ObjectId


app = FastAPI()


class EventController:
    @staticmethod
    async def create_event(
        event: CreateEventSchema, user: dict = Depends(require_user)
    ):
        # Role check - ensuring only "Coach" can create events
        if user.get("role") != "Coach":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only coaches can create events.",
            )

        # Add the user's ID to the event data as the creator
        event_data = event.dict()
        event_data["creator_id"] = user["id"]

        # Call to your service layer to save the event
        created_event = await EventService.create_event(event_data)
        if not created_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_BAD_REQUEST,
                detail="Could not create event",
            )

        # If created_event is a Pydantic model, return its .dict(), otherwise return it directly if it's already a dict
        return (
            created_event if isinstance(created_event, dict) else created_event.dict()
        )

    @staticmethod
    async def read_event(event_id: ObjectId):
        event = EventService.get_event_by_id(ObjectId(event_id))
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    async def update_event(event_id: str, event: CreateEventSchema):
        updated_event = EventService.update_event(
            ObjectId(event_id), event.dict(exclude_unset=True)
        )
        if not updated_event:
            raise HTTPException(status_code=404, detail="Event not found")
        return updated_event

    async def delete_event(event_id: ObjectId):
        result = EventService.delete_event(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return result

    async def list_events(team_id: str):
        events = EventService.list_events(team_id)
        return events


# , user: dict = Depends(require_user)
