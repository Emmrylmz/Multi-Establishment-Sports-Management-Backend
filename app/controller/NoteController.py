from fastapi import (
    HTTPException,
    status,
    APIRouter,
    Response,
    status,
    Depends,
    HTTPException,
    Request,
)
from ..models.note_schemas import NoteCreate, NoteResponse, NoteType
from datetime import datetime, timedelta
from app.config import settings
from typing import List, Dict, Any, Set
from .BaseController import BaseController
from ..service import TeamService, AuthService, UserService, NoteService
from pydantic import ValidationError


class NoteController(BaseController):
    def __init__(
        self,
        auth_service: AuthService,
        note_service: NoteService,
    ):
        super().__init__()  # Initialize the BaseController
        self.auth_service = auth_service
        self.note_service = note_service

    async def create_note(
        self,
        payload: NoteCreate,
        request: Request,
    ):
        app = request.app
        # Uncomment the following line if you want to implement role-based authentication
        # user = await self.auth_service.validate_role("Coach")

        # Create the note
        try:
            created_note = await self.note_service.create_note(payload)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        if not created_note:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create note",
            )

        # Prepare the message for RabbitMQ
        message = {
            "body": created_note.dict(),
            "action": "created",
            "note_type": payload.note_type,
        }
        print(payload.note_type, "porno")
        # Determine the routing key based on the note type
        if payload.note_type == NoteType.INDIVIDUAL:
            routing_key = f"user.{payload.recipient_id}.notification"
        elif payload.note_type == NoteType.TEAM:
            routing_key = f"team.{payload.team_id}.event.created"
        elif payload.note_type == NoteType.PROVINCE:
            routing_key = f"province.{payload.province_id}.notification"
        elif payload.note_type == NoteType.GLOBAL:
            routing_key = "all.users.notification"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid note type: {payload.note_type}",
            )

        # Publish the message to RabbitMQ
        try:
            await app.rabbit_client.publish_message(
                routing_key=routing_key,
                message=message,
            )
        except Exception as e:
            # Log the error, but don't fail the request
            print(f"Failed to publish message to RabbitMQ: {str(e)}")

        return created_note

    async def create_individual_note():
        pass
