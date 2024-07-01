from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from ..models.event_schemas import (
    CreateEventSchema,
    UpdateEventSchema,
    EventResponseSchema,
    Event,
    ListEventResponseSchema,
)
from ..models.attendance_schemas import AttendanceFormSchema
from bson import ObjectId
from .BaseController import BaseController
from typing import List, Dict, Any
from ..service import EventService, AuthService
import logging

# from ...main import rabbit_client


class EventController(BaseController):
    def __init__(self, event_service: EventService, auth_service: AuthService):
        super().__init__()  # This initializes the BaseController
        self.event_service = event_service
        self.auth_service = auth_service

    async def create_event(
        self,
        event: CreateEventSchema,
        request: Request,
        user_id: str,
    ):
        # Role check - ensuring only "Coach" can create events
        app = request.app
        user = await self.auth_service.validate_role(user_id, role="Coach")

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
        result = await self.event_service.delete(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return EventResponseSchema(event_id=event_id, status="deleted")

    async def list_events(self, team_id: str):
        logging.debug(
            f"list_events called with team_id: {team_id} of type {type(team_id)}"
        )

        if isinstance(team_id, list):
            logging.error(f"Invalid team_id type: {type(team_id)}, value: {team_id}")
            raise HTTPException(status_code=400, detail="Invalid team_id format")

        team_id = self.format_handler(team_id)
        query = {"team_id": team_id}
        events = await self.event_service.list(query)
        team = await self.team_service.get_by_id(team_id)
        response = ListEventResponseSchema(team_name=team["team_name"], events=events)
        return response

    async def get_team_events(self, team_ids: List[str]) -> List[Dict[str, Any]]:
        logging.debug(f"get_team_events called with team_ids: {team_ids}")

        # Validate and convert team_ids to ObjectIds
        try:
            team_object_ids = [ObjectId(team_id) for team_id in team_ids]
        except Exception as e:
            logging.error(f"Error converting team_ids to ObjectId: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid team_id format: {e}")

        return await self.event_service.get_upcoming_events(team_object_ids)

    async def list_events(self, team_id: str):
        logging.debug(
            f"list_events called with team_id: {team_id} of type {type(team_id)}"
        )

        if isinstance(team_id, list):
            logging.error(f"Invalid team_id type: {type(team_id)}, value: {team_id}")
            raise HTTPException(status_code=400, detail="Invalid team_id format")

        team_id = self.format_handler(team_id)
        query = {"team_id": team_id}
        events = await self.event_service.list(query)
        team = await self.team_service.get_by_id(team_id)
        response = ListEventResponseSchema(team_name=team["team_name"], events=events)
        return response

    async def add_attendance(self, attendance_form: AttendanceFormSchema):

        event_id = attendance_form.event_id
        attendances = attendance_form.attendances
        event_type = attendance_form.event_type
        team_id = attendance_form.team_id
        try:
            await self.event_service.add_attendance(
                event_id, attendances, event_type, team_id
            )
            await self.event_service.update_attendance_counts(
                event_type=event_type, attendances=attendances
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while processing attendance: {str(e)}",
            )

        return {"message": "Attendance records added successfully"}
