from fastapi import APIRouter, Depends, Request, status
from ..oauth2 import require_user
from typing import List
from ..models.constant_schemas import (
    ConstantCreate,
    ConstantResponse,
    ConstantUpdate,
    ConstantAmountGetResponse,
)
from ..controller.ConstantsController import ConstantsController
from ..dependencies.controller_dependencies import get_constants_controller

router = APIRouter()


@router.post(
    "/create", response_model=ConstantResponse, status_code=status.HTTP_201_CREATED
)
async def create_constant(
    constant: ConstantCreate,
    constant_controller: ConstantsController = Depends(get_constants_controller),
):
    return await constants_controller.create_constant(constant)


@router.get("/all", response_model=List[ConstantResponse])
async def get_all_constants(
    constant_controller: ConstantsController = Depends(get_constants_controller),
):
    return await constants_controller.get_all_constants()


@router.get("/get/{constant_id}", response_model=ConstantResponse)
async def get_constant(
    constant_id: str,
    constant_controller: ConstantsController = Depends(get_constants_controller),
):
    return await constants_controller.get_constant(constant_id)


@router.put("/update/{constant_id}", response_model=ConstantResponse)
async def update_constant(
    constant_id: str,
    constant: ConstantUpdate,
    constant_controller: ConstantsController = Depends(get_constants_controller),
):
    return await constants_controller.update_constant(constant_id, constant)


@router.delete("/delete/{constant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_constant(
    constant_id: str,
    constant_controller: ConstantsController = Depends(get_constants_controller),
):
    await constants_controller.delete_constant(constant_id)
    return None


@router.get("/get/key/{key}", response_model=ConstantAmountGetResponse)
async def get_constant_by_key(
    key: str,
    constant_controller: ConstantsController = Depends(get_constants_controller),
):
    return await constants_controller.get_constant_by_key(key)
