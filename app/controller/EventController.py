from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    status,
    Request,
    Query,
)
from pydantic import BaseModel
from ..models.event_schemas import (
    CreateEventSchema,
    UpdateEventSchema,
    EventResponseSchema,
    Event,
    ListEventResponseSchema,
    CreatePrivateLessonSchema,
    PrivateLessonResponseSchema,
    RequestStatus,
    ListEventParams,
)
from ..models.attendance_schemas import AttendanceFormSchema, AttendanceRecord
from ..models.user_schemas import UserRole
from bson import ObjectId
from typing import List, Dict, Any
from ..service import EventService, AuthService, PaymentService, TeamService
from ..redis_client import RedisClient
import logging
from datetime import datetime
from fastapi.responses import JSONResponse


class EventController:
    @classmethod
    async def create(
        cls,
        event_service: EventService,
        auth_service: AuthService,
        payment_service: PaymentService,
        team_service: TeamService,
    ):
        self = cls.__new__(cls)
        await self.__init__(event_service, auth_service, payment_service, team_service)
        return self

    def __init__(
        self,
        event_service: EventService,
        auth_service: AuthService,
        payment_service: PaymentService,
        team_service: TeamService,
    ):
        self.event_service = event_service
        self.auth_service = auth_service
        self.payment_service = payment_service
        self.team_service = team_service

    async def create_event(
        self,
        event: CreateEventSchema,
        request: Request,
        user_id: str,
    ):
        # Role check - ensuring only "Coach" can create events
        app = request.app
        user = await self.auth_service.validate_role(user_id, role=UserRole.COACH.value)

        # Add the user's ID to the event data as the creator
        event_data = event.dict()
        event_data["creator_name"] = user["name"]
        event_data["team_id"] = event_data["team_id"]
        # Call to your service layer to save the event asynchronously
        created_event = await self.event_service.create(event_data)
        print("created_event", created_event)
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
        try:
            data_id = ObjectId(event_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid event ID")

        updated_event = await self.event_service.update(
            str(data_id), event.dict(exclude_unset=True)
        )

        if updated_event is None:
            raise HTTPException(status_code=404, detail="Event not found")

        return EventResponseSchema(event_id=event_id, status="changed")

    async def delete_event(self, event_id: str):
        result = await self.event_service.delete(ObjectId(event_id))
        # raise HTTPException(status_code=404, detail="Event not found")
        return EventResponseSchema(event_id=event_id, status="deleted")

    async def get_team_events(
        self, team_ids: List[str], page: int
    ) -> List[Dict[str, Any]]:
        logging.debug(f"get_team_events called with team_ids: {team_ids}")

        # Validate and convert team_ids to ObjectIds
        try:
            team_object_ids = [ObjectId(team_id) for team_id in team_ids]
        except Exception as e:
            logging.error(f"Error converting team_ids to ObjectId: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid team_id format: {e}")

        return await self.event_service.get_all_events_by_team_id(
            team_object_ids, page=page
        )

    async def add_attendance(self, attendance_form: AttendanceFormSchema):
        event_id = attendance_form.event_id
        attendances = attendance_form.attendances

        try:
            result = await self.event_service.add_attendance(
                event_id=event_id, attendances=attendances
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while processing attendance: {str(e)}",
            )

        return {"message": "Attendance records added successfully"}

    async def fetch_attendances_for_event(self, event_id: str):
        return await self.event_service.get_attendances_by_event_id(event_id)

    async def get_events(self, params: ListEventParams) -> ListEventResponseSchema:
        print(params)
        return await self.event_service.get_events(params)

    async def update_attendances(
        self, attendances: List[AttendanceRecord], event_id: str
    ):
        return await self.event_service.update_attendance(attendances, event_id)

    async def create_private_lesson_request(
        self,
        lesson: CreatePrivateLessonSchema,
        request: Request,
        # user_id: str,
    ):
        app = request.app

        # Create a private lesson request
        lesson_request_id = await self.event_service.create_private_lesson_request(
            lesson
        )
        if not lesson_request_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create private lesson request",
            )

        return {"request_id": str(lesson_request_id), "status": "request_created"}

    async def approve_private_lesson(
        self,
        lesson_data: CreatePrivateLessonSchema,
        lesson_id: str,
        user_id: str,
        request: Request,
    ):
        try:
            user = await self.auth_service.validate_role(
                user_id, role=UserRole.COACH.value
            )
            app = request.app

            if not lesson_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="lesson_id is required",
                )

            # Fetch the existing lesson request
            existing_request = await self.event_service.get_private_lesson_by_id(
                ObjectId(lesson_id)
            )

            print(f"Existing request: {existing_request}")  # Debug print

            if not existing_request:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Private lesson request not found",
                )

            # Check if the request is still pending
            if existing_request.get("request_status") != RequestStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot approve a request that is not pending",
                )

            # Prepare the update data
            update_data = {
                "place": lesson_data.place,
                "start_datetime": lesson_data.start_datetime,
                "end_datetime": lesson_data.end_datetime,
                "description": lesson_data.description,
                "lesson_fee": lesson_data.lesson_fee,
                "paid": lesson_data.paid,
                "coach_id": user["_id"],  # Replace with actual coach ID if necessary
                "request_status": RequestStatus.APPROVED,
                "response_date": datetime.utcnow(),
                "response_notes": lesson_data.response_notes,
            }

            # Approve the private lesson request
            updated_count = await self.event_service.approve_private_lesson_request(
                lesson_id, update_data
            )

            if not updated_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not approve private lesson request",
                )

            # Fetch the updated lesson data
            created_lesson = await self.event_service.get_private_lesson_by_id(
                {"_id": ObjectId(lesson_id)}
            )

            if not created_lesson:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not fetch approved lesson data",
                )

            created_payment = (
                await self.payment_service.create_payment_for_private_lesson(
                    created_lesson=created_lesson,
                    has_paid=lesson_data.paid,
                    province=user["province"],
                )
            )

            if not created_payment:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not create payment for the lesson",
                )

            # Publishing a message to RabbitMQ asynchronously
            await app.rabbit_client.publish_message(
                routing_key="private_lesson.approved",
                message={"lesson": created_lesson, "action": "approved"},
            )

            return {
                "lesson_id": str(created_lesson["_id"]),
                "status": "lesson_approved",
            }

        except HTTPException as http_exc:
            print(
                f"HTTPException caught: status_code={http_exc.status_code}, detail={http_exc.detail}"
            )
            return JSONResponse(
                status_code=http_exc.status_code, content={"detail": http_exc.detail}
            )
        except Exception as e:
            print(f"Unexpected error approving private lesson: {str(e)}")
            print("Type of exception:", type(e))
            print("Exception args:", e.args)
            import traceback

            traceback.print_exc()

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": f"Unexpected error approving private lesson: {str(e)}"
                },
            )

    async def get_private_lesson_by_coach_id(self, coach_id: str):
        return await self.event_service.get_private_lesson_by_user_id(
            id=coach_id, field="coach_id"
        )

    async def get_private_lesson_by_player_id(self, player_id: str):
        return await self.event_service.get_private_lesson_by_user_id(
            id=player_id, field="player_id"
        )
