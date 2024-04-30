from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ..tools.RabbitClient import RabbitClient
from ..models import event_schemas
from ..database import Event

app = FastAPI()


class EventController:
    @staticmethod
    async def create_event(event: Union[CreateEventSchema, CreateGameEventSchema]):
        event_dict = event.dict()
        event_dict["created_at"] = (
            datetime.now()
        )  # Ensure the timestamp is set at creation time

        # You might want to save the event to a database here
        # For example: db.save_event(event_dict)

        # Publish event creation to RabbitMQ
        await publish_event_message(event_dict)

        return event_dict


@app.post("/events/")
async def create_event(event: Event):
    # Logic to save event to database or process otherwise
    # Here you would typically insert the event into your database

    # Publish message to RabbitMQ
    message = {"team_id": event.team_id, "message": f"New event: {event.description}"}
    try:
        await RabbitClient.publish_message("team_notifications", message)
        return {"message": "Event created and players notified!", "data": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
