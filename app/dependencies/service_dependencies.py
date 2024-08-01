# dependencies.py
from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..database import get_database
from ..redis_client import RedisClient
from ..service.TokenService import PushTokenService
from ..service.TeamService import TeamService
from ..service.EventService import EventService
from ..service.UserService import UserService
from ..service.AuthService import AuthService
from ..service.PaymentService import PaymentService
from ..service.ConstantsService import ConstantsService
from ..service.NoteService import NoteService
from ..redis_client.RedisClient import get_redis_client


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.mongodb


def get_redis(request: Request) -> RedisClient:
    return request.app.redis_client


async def get_event_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await EventService.create(db, redis)


async def get_auth_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await AuthService.create(db, redis)


async def get_payment_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await PaymentService.create(db, redis)


async def get_team_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await TeamService.create(db, redis)


async def get_push_token_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await PushTokenService.create(db, redis)


async def get_constants_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await ConstantsService.create(db, redis)


async def get_note_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await NoteService.create(db, redis)


async def get_user_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis_client),
):
    return await UserService.create(db, redis)
