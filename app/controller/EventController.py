from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from ..models.event_schemas import CreateEventSchema
from bson import ObjectId
from .BaseController import BaseController

# from ...main import rabbit_client


class EventController(BaseController):
    async def create_event(
        self,
        event: CreateEventSchema,
        request: Request,
        user: dict,
    ):
        # Role check - ensuring only "Coach" can create events
        app = request.app
        self.auth_service.validate_role(user=user, role="Coach")

        # Add the user's ID to the event data as the creator
        event_data = event.dict()
        event_data["creator_id"] = ensure_object_id(user["_id"])
        event_data["team_id"] = self.format_handler(event_data["team_id"])
        # Call to your service layer to save the event asynchronously
        created_event = await self.event_service.create(event_data)
        if not created_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create event",
            )

        # Publishing a message to RabbitMQ asynchronously
        await app.rabbit_client.publish_message(
            routing_key=f"team.{event_data['team_id']}.event.created",
            message={"event": created_event, "action": "created"},
        )
        return created_event

    async def read_event(self, event_id: str):
        event = await self.event_service.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    async def update_event(self, event_id: str, event: CreateEventSchema):
        # update
        updated_event = await self.event_service.update(
            ObjectId(event_id), event.dict(exclude_unset=True)
        )
        if not updated_event:
            raise HTTPException(status_code=404, detail="Event not found")
        return updated_event

    async def delete_event(self, event_id: str):
        result = await self.event_service.delete_event(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return result

    async def list_events(self, team_id: str):
        team_id = ensure_object_id(team_id)
        query = {"team_id": team_id}
        events = await self.event_service.list(query)
        return events
