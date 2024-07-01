from fastapi import APIRouter, Depends, Request, status
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


user_router = router
