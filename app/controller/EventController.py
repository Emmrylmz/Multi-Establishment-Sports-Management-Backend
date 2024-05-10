from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from app.service.EventService import EventService
from ..oauth2 import require_user
from ..models.event_schemas import CreateEventSchema
from bson import ObjectId
<<<<<<< HEAD
from ..service.UserService import user_service
from ..service.EventService import event_service
=======
from ..service.UserService import UserService, user_service
from datetime import datetime


>>>>>>> rabbit_stann

# from ...main import rabbit_client


<<<<<<< HEAD
=======


>>>>>>> rabbit_stann
class EventController:
    event_service = EventService(Event)
    
    @staticmethod
    async def create_event(event: CreateEventSchema, request: Request, user: dict):
        app = request.app
<<<<<<< HEAD
        await user_service.validate_role(user=user, role="Coach")

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
            queue=event_data["team_id"],
            message=event_response,  # Ensure this is serializable or serialized
        )

        return event_response

    @staticmethod
    async def read_event(event_id: str):
        event = event_service.get_by_id(event_id)
=======
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
>>>>>>> rabbit_stann
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
<<<<<<< HEAD
    async def update_event(event_id: str, event: CreateEventSchema):
        # update
        updated_event = event_service.update(
=======
    async def update_event(self, event_id: str, event: CreateEventSchema, request: Request):
        updated_event = await EventController.event_service.update_event(
>>>>>>> rabbit_stann
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

<<<<<<< HEAD
    async def delete_event(event_id: str):
        result = event_service.delete_event(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return result

    def list_events(query: dict):
        events = event_service.list(query)
=======

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
>>>>>>> rabbit_stann
        return events


# , user: dict = Depends(require_user)
