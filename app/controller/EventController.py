from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from ..models.event_schemas import (
    CreateEventSchema,
    UpdateEventSchema,
    EventResponseSchema,
    Event,
    ListEventResponseSchema,
)
from bson import ObjectId
from .BaseController import BaseController
from typing import List, Dict, Any

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
        event_data["creator_name"] = user["name"]
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
        return EventResponseSchema(event_id=created_event["_id"], status="created")

    async def read_event(self, event_id: str):
        event = await self.event_service.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    async def update_event(self, event_id: str, event: UpdateEventSchema):
        # update
        data_id = self.format_handler(event_id)
        updated_event = await self.event_service.update(
            data_id, event.dict(exclude_unset=True)
        )
        if not updated_event:
            raise HTTPException(status_code=404, detail="Event not found")
        return EventResponseSchema(event_id=event_id, status="changed")

    async def delete_event(self, event_id: str):
        result = await self.event_service.delete_event(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return EventResponseSchema(event_id=event_id, status="deleted")

    async def list_events(self, team_id: str):
        team_id = self.format_handler(team_id)
        query = {"team_id": team_id}
        events = await self.event_service.list(query)
        team = await self.team_service.get_by_id(team_id)
        response = ListEventResponseSchema(team_name=team["team_name"], events=events)
        return response

    async def get_team_events(self, team_ids: List[str]) -> List[Dict[str, Any]]:

        team_object_ids = [self.format_handler(team_id) for team_id in team_ids]

        return await self.event_service.get_upcoming_events(team_object_ids)
