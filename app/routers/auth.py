from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fastapi import Response, status, Depends, HTTPException, APIRouter, Request
from app import oauth2
from .. import utils
from ..models.user_schemas import (
    LoginUserSchema,
    CreateUserSchema,
    UserAttributesSchema,
    UserResponseSchema,
    EmailSchema,
)
from app.oauth2 import AuthJWT
from ..config import settings
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT
from ..models.firebase_token_schemas import PushTokenSchema
from ..controller.AuthController import AuthController
from ..dependencies.controller_dependencies import get_auth_controller

ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: CreateUserSchema,
    auth_controller: AuthController = Depends(get_auth_controller),
):
    return await auth_controller.register_user(payload)


@router.post("/push_token", status_code=status.HTTP_201_CREATED)
async def get_push_token(
    payload: PushTokenSchema,
    user_id: str = Depends(oauth2.require_user),
    auth_controller: AuthController = Depends(get_auth_controller),
):
    return await auth_controller.get_push_token(payload, user_id)


@router.post("/login", response_model=UserResponseSchema)
async def login(
    payload: LoginUserSchema,
    Authorize: AuthJWT = Depends(),
    auth_controller: AuthController = Depends(get_auth_controller),
    response: Response = None,
):
    return await auth_controller.login_user(payload, Authorize, response=response)


@router.post("/checkToken")
async def access_protected_resource(
    Authorize: AuthJWT = Depends(),
    auth_controller: AuthController = Depends(get_auth_controller),
):
    # If the function returns without error, it means the user is authenticated and verified
    return {"message": "You have access to this protected resource"}


# @router.get("/refresh_token")
# async def refresh_token(
#     response: Response,
#     Authorize: AuthJWT = Depends(),
#     auth_controller: AuthController = Depends(get_auth_controller),
# ):
#     return await auth_controller.refresh_access_token(response, Authorize)


@router.get("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    Authorize: AuthJWT = Depends(),
    auth_controller: AuthController = Depends(get_auth_controller),
):
    return auth_controller.logout(response, Authorize)


@router.get("/delete_user/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    # Authorize: AuthJWT = Depends(),
    user_id: str,
    auth_controller: AuthController = Depends(get_auth_controller),
):
    return await auth_controller.delete_user(user_id=user_id)  # , Authorize


@router.post("/forgot-password")
async def forgot_password(email: EmailSchema):
    reset_token = await db.reset_tokens.find_one(
        {"token": reset_data.token, "expires": {"$gt": datetime.utcnow()}}
    )
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    hashed_password = pwd_context.hash(reset_data.new_password)
    await db.users.update_one(
        {"_id": reset_token["user_id"]}, {"$set": {"password": hashed_password}}
    )
    await db.reset_tokens.delete_one({"_id": reset_token["_id"]})
    return {"message": "Password reset successful"}


# @router.get("/inspect-celery")
# def inspect_celery_endpoint(request: Request):
#     app = request.app
#     celery_app = app.celery_app
#     result = inspect_celery_tasks(celery_app)
#     return {"message": "Celery inspection complete", "result": result}


# def inspect_celery_tasks(celery_app):
#     # Create an inspect instance
#     i = celery_app.control.inspect()

#     # Get scheduled tasks
#     scheduled = i.scheduled()

#     if scheduled:
#         for worker, tasks in scheduled.items():
#             print(f"Scheduled tasks for worker {worker}:")
#             for task in tasks:
#                 print(f"  - {task['name']} : {task['schedule']}")
#     else:
#         print("No scheduled tasks found.")

#     # Check registered tasks
#     registered = i.registered()
#     if registered:
#         for worker, tasks in registered.items():
#             print(f"Registered tasks for worker {worker}:")
#             for task in tasks:
#                 print(f"  - {task}")
#     else:
#         print("No registered tasks found.")
