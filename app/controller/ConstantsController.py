from fastapi import HTTPException, status
from ..models.constant_schemas import ConstantCreate, ConstantUpdate, ConstantResponse
from typing import List, Optional
from ..service.ConstantsService import ConstantsService


class ConstantsController:
    @classmethod
    async def create(cls, constants_service: ConstantsService):
        self = cls.__new__(cls)
        await self.__init__(constants_service)
        return self

    def __init__(self, constants_service: ConstantsService):
        self.constants_service = constants_service

    async def create_constant(self, constant: ConstantCreate) -> ConstantResponse:
        try:
            return await self.constants_service.create_constant(constant)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def update_constant(
        self, constant_id: str, constant: ConstantUpdate
    ) -> ConstantResponse:
        try:
            return await self.constants_service.update_constant(constant_id, constant)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def get_all_constants(self) -> List[ConstantCreate]:
        try:
            return await self.constants_service.get_all_constants()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def get_constant(self, constant_id: str) -> ConstantCreate:
        try:
            constant = await self.constants_service.get_constant(constant_id)
            if constant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Constant not found"
                )
            return constant
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def delete_constant(self, constant_id: str) -> bool:
        try:
            return await self.constants_service.delete_constant(constant_id)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def get_constant_by_key(self, key: str) -> Optional[ConstantResponse]:
        try:
            constant = await self.constants_service.get_constant_by_key(key)
            if constant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Constant not found"
                )
            return constant
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
