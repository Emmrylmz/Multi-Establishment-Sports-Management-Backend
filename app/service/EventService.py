from bson import ObjectId
from datetime import datetime
from app.database import Event  # Assuming 'Event' is your MongoDB collection
from app.serializers.eventSerializers import eventEntity


class EventService:
    @staticmethod
    async def create_event(event_data: dict):
        """Creates a new event and stores it in the database."""
        event_data["created_at"] = datetime.utcnow()

        result = Event.insert_one(
            event_data
        )  # Assuming Event is your MongoDB collection
        return EventService.get_event_by_id(result.inserted_id)

    @staticmethod
    def get_event_by_id(event_id: ObjectId) -> dict:
        """Retrieves a single event by its ID."""
        event = Event.find_one({"_id": event_id})
        return eventEntity(event) if event else None

    @staticmethod
    def update_event(event_id: ObjectId, update_data: dict) -> dict:
        """Updates an existing event."""
        Event.update_one({"_id": event_id}, {"$set": update_data})
        return EventService.get_event_by_id(event_id)

    @staticmethod
    def delete_event(event_id: ObjectId) -> bool:
        """Deletes an event by its ID."""
        result = Event.delete_one({"_id": event_id})
        return result.deleted_count > 0

    @staticmethod
    def list_events() -> list:
        """Lists all events."""
        events = Event.find({})
        return [eventEntity(event) for event in events]
