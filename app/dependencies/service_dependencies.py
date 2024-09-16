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
from ..repositories.EventRepository import EventRepository
from ..repositories.AuthRepository import AuthRepository
from ..repositories.PaymentRepository import PaymentRepository
from ..repositories.TeamRepository import TeamRepository


def get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.mongodb


def get_redis(request: Request) -> RedisClient:
    return request.app.redis_client


async def get_event_repository(
    database: AsyncIOMotorDatabase = Depends(get_db),
) -> EventRepository:
    return await EventRepository.initialize(database=database)


async def get_auth_repository(
    database: AsyncIOMotorDatabase = Depends(get_db),
) -> AuthRepository:
    return await AuthRepository.initialize(database=database)


async def get_team_repository(
    database: AsyncIOMotorDatabase = Depends(get_db),
) -> TeamRepository:
    return await TeamRepository.initialize(database=database)


async def get_payment_repository(
    database: AsyncIOMotorDatabase = Depends(get_db),
) -> PaymentRepository:
    return await PaymentRepository.initialize(database=database)


async def get_event_service(
    event_repository: EventRepository = Depends(get_event_repository),
    redis: RedisClient = Depends(get_redis),
):
    return await EventService.initialize(
        event_repository=event_repository, redis_client=redis
    )


async def get_auth_service(
    auth_repository: AuthRepository = Depends(get_auth_repository),
    redis: RedisClient = Depends(get_redis),
):
    return await AuthService.initialize(
        auth_repository=auth_repository, redis_client=redis
    )


async def get_payment_service(
    payment_repository: PaymentRepository = Depends(get_payment_repository),
    redis: RedisClient = Depends(get_redis),
):
    return await PaymentService.initialize(
        payment_repository=payment_repository, redis_client=redis
    )


async def get_team_service(
    team_repository: TeamRepository = Depends(get_team_repository),
    redis: RedisClient = Depends(get_redis),
):
    return await TeamService.initialize(
        team_repository=team_repository, redis_client=redis
    )


async def get_push_token_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    return await PushTokenService.initialize(db, redis)


async def get_constants_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    return await ConstantsService.initialize(db, redis)


async def get_note_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    return await NoteService.initialize(db, redis)


async def get_user_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    return await UserService.initialize(db, redis)
