from fastapi import APIRouter, Depends, Request, status, Query
from ..oauth2 import require_user
from ..models.user_schemas import UserAttributesSchema
from ..controller.UserController import UserController
from ..controller.UserController import UserController
from ..dependencies.controller_dependencies import get_user_controller

router = APIRouter()


@router.post("/update", status_code=status.HTTP_200_OK)
async def update_user_information(
    payload: UserAttributesSchema,
    user_id: str = Depends(require_user),
    user_controller: UserController = Depends(get_user_controller),
):
    """
    Update user information.
    """
    return await user_controller.update_user_information(payload, user_id)


@router.post("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_information(
    user_id: str,
    user_controller: UserController = Depends(get_user_controller),
):
    """
    Get user information.
    """
    return await user_controller.get_user_information(user_id)


@router.get("/users/search")
async def search_users(
    query: str = Query(None),
    province: str = Query(None),
    user_controller: UserController = Depends(get_user_controller),
):
    if not query:
        # If no query is provided, return users by province
        users = await user_controller.get_all_users_by_province(province)
    else:
        # Search users based on the query
        users = await user_controller.search_users_by_name(query)
    return users


user_router = router
