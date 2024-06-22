from fastapi import APIRouter, status, Depends, HTTPException, Request
from ..controller.EventController import EventController
from ..models.event_schemas import (
    CreateEventSchema,
    ListTeamEventSchema,
    UpdateEventSchema,
    EventResponseSchema,
)
from ..oauth2 import require_user
from .BaseRouter import BaseRouter
from fastapi_jwt_auth import AuthJWT


class EventRouter(BaseRouter):
    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter()
        self._init_routes()

    def _init_routes(self) -> None:
        @self.router.post(
            "/create",
            status_code=status.HTTP_201_CREATED,
            response_model=EventResponseSchema,
        )
        async def create_event(
            payload: CreateEventSchema,
            request: Request,
            user: dict = Depends(require_user),
        ):
            return await self.event_controller.create_event(payload, request, user)

        @self.router.get("/{event_id}", status_code=status.HTTP_200_OK)
        async def get_event(event_id: str):
            return await self.event_controller.read_event(event_id)

        @self.router.delete(
            "/delete/{event_id}",
            response_model=EventResponseSchema,
            status_code=status.HTTP_200_OK,
        )
        async def delete_event(event_id: str):
            return await self.event_controller.delete_event(event_id)

        @self.router.post("/list")
        async def list_events(request: ListTeamEventSchema):
            return await self.event_controller.list_events(request.team_id)

        @self.router.post(
            "/update/{event_id}",
            response_model=EventResponseSchema,
            status_code=status.HTTP_200_OK,
        )
        async def update_event(event_id: str, payload: UpdateEventSchema):
            return await self.event_controller.update_event(event_id, payload)

        @self.router.post("/get_team_events")
        async def fetch_team_events(
            team_ids: ListTeamEventSchema, user: dict = Depends(self.get_current_user)
        ):
            team_events = await self.event_controller.get_team_events(team_ids.team_id)
            return team_events


event_router = EventRouter().router
