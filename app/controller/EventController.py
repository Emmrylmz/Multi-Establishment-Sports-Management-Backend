from fastapi import FastAPI, HTTPException, Depends, status, Request
from pydantic import BaseModel
from ..database import Event, User
from app.service.EventService import EventService
from ..oauth2 import require_user
from ..models.event_schemas import CreateEventSchema
from bson import ObjectId
from ..service.UserService import UserService, user_service
from datetime import datetime



# from ...main import rabbit_client




class EventController:
    event_service = EventService(Event)
    
    @staticmethod
    async def create_event(event: CreateEventSchema, request: Request, user: dict):
        app = request.app
        await user_service.validate_role(user, "Coach")
        event_data = event.dict()
        event_data['creator_id'] = user['id']
        
        if isinstance(event_data.get('event_date'), datetime):
            event_data['event_date'] = event_data['event_date'].isoformat()

        created_event = await EventController.event_service.create(event_data)
        if not created_event:
            raise HTTPException(status_code=400, detail="Could not create event")


        await request.app.rabbit_client.publish_message(
            routing_key=f"team.{event_data['team_id']}.event.created",
            message={
                "event": event.dict(),  # Convert the Pydantic model to a dictionary here
                "action": "created"
            }
        )

        # # Publish a message that an event has been created
        # await request.app.rabbit_client.publish_message(
        #     routing_key=f"team.{event_data['team_id']}.event.created",
        #     message={"event": event, "action": "created"}
        # )
        return created_event

    @staticmethod
    async def read_event(self, event_id: ObjectId):
        event = await self.event_service.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    async def update_event(self, event_id: str, event: CreateEventSchema, request: Request):
        updated_event = await EventController.event_service.update_event(
            ObjectId(event_id), event.dict(exclude_unset=True)
        )
        if not updated_event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Publish a message that an event has been updated
        await request.app.rabbit_client.publish_message(
            routing_key=f"team.{updated_event['team_id']}.event.updated",
            message={"event_id": event_id, "action": "updated"}
        )
        return updated_event


    @staticmethod
    async def delete_event(self, event_id: str, request: Request):
        deleted = EventController.event_service.delete_event(ObjectId(event_id))
        if not deleted:
            raise HTTPException(status_code=404, detail="Event not found")

        # Publish a message that an event has been deleted
        await request.app.rabbit_client.publish_message(
            routing_key=f"team.{deleted['team_id']}.event.deleted",
            message={"event_id": event_id, "action": "deleted"}
        )
        return {"status": "Event deleted"}

    async def list_events(self, team_id: str):
        events = self.event_service.list_events(team_id)
        return events


# , user: dict = Depends(require_user)
