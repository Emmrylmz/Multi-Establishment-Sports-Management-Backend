from fastapi import APIRouter, status, Depends, HTTPException, Request, BackgroundTasks
from ..controller.EventController import EventController
from ..models.event_schemas import (
    CreateEventSchema,
    ListTeamEventSchema,
    UpdateEventSchema,
    EventResponseSchema,
    CreatePrivateLessonSchema,
)
from ..models.attendance_schemas import (
    AttendanceFormSchema,
    FetchAttendanceFromEventIdSchema,
    UpdateAttendanceSchema,
)
from ..oauth2 import require_user
from ..dependencies.controller_dependencies import get_event_controller
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
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.create_event(payload, request, user_id)


@router.get("/{event_id}", status_code=status.HTTP_200_OK)
async def get_event(
    event_id: str,
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.read_event(event_id)


@router.delete(
    "/delete/{event_id}",
    response_model=EventResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def delete_event(
    event_id: str,
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.delete_event(event_id)


@router.post(
    "/update/{event_id}",
    response_model=EventResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_event(
    event_id: str,
    payload: UpdateEventSchema,
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.update_event(event_id, payload)


@router.post("/get_team_events")
async def fetch_team_events(
    team_ids: ListTeamEventSchema,
    user_id: str = Depends(require_user),
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.get_team_events(team_ids.team_ids)


@router.post("/add_attendances_to_event")
async def add_attendances_to_event(
    attendance_form: AttendanceFormSchema,
    # user_id: str = Depends(require_user),
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.add_attendance(attendance_form=attendance_form)


@router.post("/fetch_attendances_for_event")
async def fetch_attendances_for_event(
    payload: FetchAttendanceFromEventIdSchema,
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.fetch_attendances_for_event(payload.event_id)


@router.post("/get_upcoming_events")
async def get_upcoming_events(
    payload: ListTeamEventSchema,
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.get_upcoming_events(payload.team_ids)


@router.put("/update_attendances")
async def update_attendances(
    payload: UpdateAttendanceSchema,
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.update_attendances(
        attendances=payload.attendances,
        event_id=payload.event_id,
        event_type=payload.event_type,
    )


@router.post("/create/private_lesson")
async def create_private_lesson_request(
    payload: CreatePrivateLessonSchema,
    request: Request,
    # user_id: str = Depends(require_user),
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.create_private_lesson_request(payload, request)


@router.post("/approve/private_lesson_response/{lesson_id}")
async def approve_private_lesson_request(
    payload: CreatePrivateLessonSchema,
    request: Request,
    lesson_id: str,
    user_id: str = Depends(require_user),
    event_controller: EventController = Depends(get_event_controller),
):
    return await event_controller.approve_private_lesson(
        lesson_data=payload, request=request, lesson_id=lesson_id, user_id=user_id
    )


@router.get("/coach_private_lessons/{coach_id}")
async def fetch_coach_private_lessons(
    coach_id: str,
    event_controller: EventController = Depends(get_event_controller),
    # user_id: str = Depends(require_user),
):
    return await event_controller.get_private_lesson_by_coach_id(coach_id)


@router.get("/player_private_lessons/{player_id}")
async def fetch_coach_private_lessons(
    player_id: str,
    event_controller: EventController = Depends(get_event_controller),
    # user_id: str = Depends(require_user),
):
    return await event_controller.get_private_lesson_by_player_id(player_id)


# @router.post("/create/private_lesson_request", response_model=PrivateLessonRequestOut)
# async def create_private_lesson_request(
#     Request: Request,
#     payload: PrivateLessonRequestCreate,
#     # current_user: dict = Depends(get_current_user),
#   event_controller: EventController = Depends(get_event_controller),

# ):
#     return await event_controller.create_private_lesson_request(
#         Request, payload
#     )
