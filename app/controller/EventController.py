from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from app.service.EventService import EventService
from ..oauth2 import require_user
from ..models.event_schemas import CreateEventSchema
from bson import ObjectId
from ..service.UserService import user_service
from ..service.EventService import event_service
from ..utils import DateTimeEncoder

# from ...main import rabbit_client


class EventController:
    @staticmethod
    async def create_event(
        event: CreateEventSchema, request: Request, user: dict = Depends(require_user)
    ):
        # Role check - ensuring only "Coach" can create events
        app = request.app
        user_service.validate_role(user=user, role="Coach")

        # Add the user's ID to the event data as the creator
        event_data = event.dict()
        event_data["creator_id"] = user["_id"]

        # Call to your service layer to save the event asynchronously
        created_event = await event_service.create(event_data)
        if not created_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create event",
            )

        # Assuming created_event returns a dict or a Pydantic model
        event_response = (
            created_event.dict() if hasattr(created_event, "dict") else created_event
        )
        # Publishing a message to RabbitMQ asynchronously
        await app.rabbit_client.publish_message(
            routing_key=f"team.{event_data['team_id']}.event.created",
            message={"event": event, "action": "created"},
        )
        return event_response

    @staticmethod
    async def read_event(event_id: str):
        event = event_service.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    async def update_event(event_id: str, event: CreateEventSchema):
        # update
        updated_event = event_service.update(
            ObjectId(event_id), event.dict(exclude_unset=True)
        )
        if not updated_event:
            raise HTTPException(status_code=404, detail="Event not found")
        return updated_event

    async def delete_event(event_id: str):
        result = event_service.delete_event(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return result

    def list_events(query: dict):
        events = event_service.list(query)
        return events


# , user: dict = Depends(require_user)
