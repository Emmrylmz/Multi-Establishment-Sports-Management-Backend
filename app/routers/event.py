from fastapi import APIRouter, status, Depends, HTTPException, Request
from ..controller.EventController import EventController
from ..models.event_schemas import (
    CreateEventSchema,
    ListTeamEventSchema,
    UpdateEventSchema,
    EventResponseSchema,
)
from ..models.attendance_schemas import (
    AttendanceFormSchema,
    FetchAttendanceFromEventIdSchema,
)
from ..oauth2 import require_user
from .BaseRouter import BaseRouter, get_base_router
from fastapi_jwt_auth import AuthJWT
from typing import Dict

router = APIRouter()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    response_model=EventResponseSchema,
)
async def create_event(
    payload: CreateEventSchema,
    request: Request,
    user_id: str = Depends(require_user),
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.event_controller.create_event(payload, request, user_id)


@router.get("/{event_id}", status_code=status.HTTP_200_OK)
async def get_event(
    event_id: str,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.event_controller.read_event(event_id)


@router.delete(
    "/delete/{event_id}",
    response_model=EventResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def delete_event(
    event_id: str,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.event_controller.delete_event(event_id)


# @router.post("/list")
# async def list_events(
#     request: ListTeamEventSchema,
#     base_router: BaseRouter = Depends(get_base_router),
# ):
#     return await base_router.event_controller.list_events(request.team_id)


@router.post(
    "/update/{event_id}",
    response_model=EventResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_event(
    event_id: str,
    payload: UpdateEventSchema,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.event_controller.update_event(event_id, payload)


@router.post("/get_team_events")
async def fetch_team_events(
    team_ids: ListTeamEventSchema,
    user_id: str = Depends(require_user),
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.event_controller.get_team_events(team_ids.team_id)


@router.post("/add_attendances_to_event")
async def add_attendances_to_event(
    attendance_form: AttendanceFormSchema,
    # user_id: str = Depends(require_user),
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.event_controller.add_attendance(
        attendance_form=attendance_form
    )


@router.post("/fetch_attendances_for_event")
async def fetch_attendances_for_event(
    payload: FetchAttendanceFromEventIdSchema,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.event_controller.fetch_attendances_for_event(
        payload.event_id
    )
