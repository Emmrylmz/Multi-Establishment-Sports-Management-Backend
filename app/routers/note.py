from fastapi import APIRouter, status, Depends, HTTPException, Request
from ..models.note_schemas import NoteCreate, NoteResponse

from ..oauth2 import require_user
from .BaseRouter import BaseRouter, get_base_router
from fastapi_jwt_auth import AuthJWT
from typing import Dict

router = APIRouter()


@router.post(
    "/create", status_code=status.HTTP_201_CREATED, response_model=NoteResponse
)
async def create_note(
    payload: NoteCreate,
    # Authorize: AuthJWT = Depends(),
    base_router: BaseRouter = Depends(get_base_router),
    request: Request = None,
):
    return await base_router.note_controller.create_note(payload, request=request)
