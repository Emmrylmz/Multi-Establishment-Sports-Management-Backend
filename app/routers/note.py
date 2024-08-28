from fastapi import APIRouter, status, Depends, HTTPException, Request
from ..models.note_schemas import NoteCreate, NoteResponse
from ..controller.NoteController import NoteController
from ..dependencies.controller_dependencies import get_note_controller
from ..oauth2 import require_user
from fastapi_jwt_auth import AuthJWT
from typing import Dict

router = APIRouter()


@router.post(
    "/create", status_code=status.HTTP_201_CREATED, response_model=NoteResponse
)
async def create_note(
    payload: NoteCreate,
    # Authorize: AuthJWT = Depends(),
    note_controller: NoteController = Depends(get_note_controller),
    request: Request = None,
):
    return await note_controller.create_note(payload, request=request)


@router.get(
    "/read/{note_id}", status_code=status.HTTP_201_CREATED, response_model=NoteResponse
)
async def create_note(
    payload: NoteCreate,
    # Authorize: AuthJWT = Depends(),
    note_controller: NoteController = Depends(get_note_controller),
    request: Request = None,
):
    return await note_controller.read_note(payload, request=request)
