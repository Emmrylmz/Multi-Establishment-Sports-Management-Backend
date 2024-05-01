from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from ..tools.RabbitClient import RabbitClient
from ..models import event_schemas
from ..database import Event
from app.service.EventService import EventService
from ..oauth2 import require_user
from ..models.event_schemas import CreateEventSchema

app = FastAPI()


class EventController:
    @staticmethod
    async def create_event(event, user: dict = Depends(require_user)):

        # if user["role"] != "Coach":
        #     raise HTTPException(
        #         status_code=403, detail="Only coaches can create events."
        #     )
        event_data = event.dict()
        # event_data["creator_id"] = user[
        #     "id"
        # ]  # Assuming the user dict has an 'id' field
        created_event = await EventService.create_event(event_data)
        if not created_event:
            raise HTTPException(status_code=400, detail="Could not create event")
        return created_event

        if isinstance(created_event, CreateEventSchema):
            return created_event
        else:
            return created_event.dict()  # Convert to dict if necessary

    @staticmethod
    async def read_event(event_id: str, user: dict = Depends(require_user)):
        event = EventService.get_event_by_id(ObjectId(event_id))
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

    @staticmethod
    async def update_event(
        event_id: str, event: CreateEventSchema, user: dict = Depends(require_user)
    ):
        updated_event = EventService.update_event(
            ObjectId(event_id), event.dict(exclude_unset=True)
        )
        if not updated_event:
            raise HTTPException(status_code=404, detail="Event not found")
        return updated_event

    async def delete_event(event_id: str, user: dict = Depends(require_user)):
        if not EventService.delete_event(ObjectId(event_id)):
            raise HTTPException(status_code=404, detail="Event not found")
        return {"message": "Event deleted successfully"}

    async def list_events(user: dict = Depends(require_user)):
        events = EventService.list_events()
        return events
