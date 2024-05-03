from fastapi import FastAPI, HTTPException, Depends, status, Request
from pydantic import BaseModel
from ..database import Event, User
from app.service.EventService import EventService
from ..oauth2 import require_user
from ..models.event_schemas import CreateEventSchema
from bson import ObjectId
from ..service.UserService import UserService


# from ...main import rabbit_client


event_service = EventService(Event)


class EventController:
    @staticmethod
    async def create_event(
        event: CreateEventSchema, request: Request, user: dict = Depends(require_user)
    ):
        # Role check - ensuring only "Coach" can create events
        app = request.app
        UserService.validate_role(user, "Coach")
        # Add the user's ID to the event data as the creator
        event_data = event.dict()
        event_data["creator_id"] = user["id"]

        # Call to your service layer to save the event
        created_event = await event_service.create(event_data)
        if not created_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_BAD_REQUEST,
                detail="Could not create event",
            )
        # If created_event is a Pydantic model, return its .dict(), otherwise return it directly if it's already a dict
        await app.rabbit_client.publish_message(
            queue="team123", message={"message": event_data}
        )
        return created_event

    @staticmethod
    async def read_event(event_id: ObjectId):
        event = event_service.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    async def update_event(event_id: str, event: CreateEventSchema):
        updated_event = event_service.update_event(
            ObjectId(event_id), event.dict(exclude_unset=True)
        )
        if not updated_event:
            raise HTTPException(status_code=404, detail="Event not found")
        return updated_event

    async def delete_event(event_id: ObjectId):
        result = event_service.delete_event(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return result

    async def list_events(team_id: str):
        events = event_service.list_events(team_id)
        return events


# , user: dict = Depends(require_user)
