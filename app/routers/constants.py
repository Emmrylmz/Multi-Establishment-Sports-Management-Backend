from fastapi import APIRouter, Depends, Request, status
from ..oauth2 import require_user
from .BaseRouter import BaseRouter, get_base_router
from typing import List
from ..models.constant_schemas import (
    ConstantCreate,
    ConstantResponse,
    ConstantUpdate,
    ConstantAmountGetResponse,
)

router = APIRouter()


@router.post(
    "/create", response_model=ConstantResponse, status_code=status.HTTP_201_CREATED
)
async def create_constant(
    constant: ConstantCreate,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.constants_controller.create_constant(constant)


@router.get("/all", response_model=List[ConstantResponse])
async def get_all_constants(
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.constants_controller.get_all_constants()


@router.get("/get/{constant_id}", response_model=ConstantResponse)
async def get_constant(
    constant_id: str,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.constants_controller.get_constant(constant_id)


@router.put("/update/{constant_id}", response_model=ConstantResponse)
async def update_constant(
    constant_id: str,
    constant: ConstantUpdate,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.constants_controller.update_constant(constant_id, constant)


@router.delete("/delete/{constant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_constant(
    constant_id: str,
    base_router: BaseRouter = Depends(get_base_router),
):
    await base_router.constants_controller.delete_constant(constant_id)
    return None


@router.get("/get/key/{key}", response_model=ConstantAmountGetResponse)
async def get_constant_by_key(
    key: str, base_router: BaseRouter = Depends(get_base_router)
):
    return await base_router.constants_controller.get_constant_by_key(key)
