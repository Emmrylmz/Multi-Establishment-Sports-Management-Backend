# dependencies.py
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from ..database import get_collection
from ..service.TokenService import PushTokenService
from ..service.TeamService import TeamService
from ..service.EventService import EventService
from ..service.UserService import UserService
from ..service.AuthService import AuthService
from ..service.PaymentService import PaymentService


def get_push_token_service(
    push_token_collection: AsyncIOMotorCollection = Depends(
        lambda: get_collection("Push_Token")
    ),
) -> PushTokenService:
    return PushTokenService(push_token_collection)


def get_team_service(
    team_collection: AsyncIOMotorCollection = Depends(lambda: get_collection("Team")),
) -> TeamService:
    return TeamService(team_collection)


def get_event_service(
    event_collection: AsyncIOMotorCollection = Depends(lambda: get_collection("Event")),
) -> EventService:
    return EventService(event_collection)


def get_user_service(
    user_collection: AsyncIOMotorCollection = Depends(
        lambda: get_collection("User_Info")
    ),
) -> UserService:
    return UserService(user_collection)


def get_auth_service(
    auth_collection: AsyncIOMotorCollection = Depends(lambda: get_collection("Auth")),
) -> AuthService:
    return AuthService(auth_collection)


def get_attendance_service(
    attendance_collection: AsyncIOMotorCollection = Depends(
        lambda: get_collection("Attendance")
    ),
) -> EventService:
    return EventService(attendance_collection)


def get_payment_service(
    payment_collection: AsyncIOMotorCollection = Depends(
        lambda: get_collection("Payment")
    ),
) -> PaymentService:
    return PaymentService(payment_collection)
