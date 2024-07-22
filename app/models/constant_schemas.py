from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ConstantCreate(BaseModel):
    key: str
    value: float
    description: str


class ConstantUpdate(BaseModel):
    value: float
    description: str


class ConstantResponse(BaseModel):
    id: str
    key: str
    value: float
    description: str
    created_at: datetime
    updated_at: Optional[datetime]


class ConstantAmountGetResponse(BaseModel):
    id: str
    value: float
