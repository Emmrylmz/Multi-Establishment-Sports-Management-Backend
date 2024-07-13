from fastapi import APIRouter, Depends, Request, status, Query
from ..oauth2 import require_user
from ..models.user_schemas import UserAttributesSchema
from ..controller.UserController import UserController
from .BaseRouter import BaseRouter, get_base_router

router = APIRouter()


@router.post("/update", status_code=status.HTTP_200_OK)
async def update_user_information(
    payload: UserAttributesSchema,
    user_id: str = Depends(require_user),
    base_router: BaseRouter = Depends(get_base_router),
):
    """
    Update user information.
    """
    return await base_router.user_controller.update_user_information(payload, user_id)


@router.post("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_information(
    user_id: str, base_router: BaseRouter = Depends(get_base_router)
):
    """
    Get user information.
    """
    return await base_router.user_controller.get_user_information(user_id)


@router.get("/users/search")
async def search_users(
    query: str = Query(None),
    province: str = Query(None),
    base_router: BaseRouter = Depends(get_base_router),
):
    if not query:
        # If no query is provided, return users by province
        users = await base_router.user_controller.get_all_users_by_province(province)
    else:
        # Search users based on the query
        users = await base_router.user_controller.search_users_by_name(query)
    return users


user_router = router
