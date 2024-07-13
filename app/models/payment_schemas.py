from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum


class PaymentType(str, Enum):
    MONTHLY = "monthly"
    PRIVATE_LESSON = "private_lesson"


class Payment(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    amount: float
    payment_type: PaymentType
    paid: bool = False
    paid_date: datetime = None
    month: int
    year: int

    class Config:
        json_encoders = {ObjectId: str}


class SingleUserPayment(BaseModel):
    user_id: str


class MonthlyRevenuePayloadSchema(BaseModel):
    year: int
    month: int


class YearlyRevenuePayloadSchema(BaseModel):
    year: int


class RevenueByMonthRangePayloadSchema(BaseModel):
    year: int
    start_month: Optional[int]
    end_month: Optional[int]


class PrivateLessonResponseSchema(BaseModel):
    lesson_id: str
    status: str


class CreatePaymentForMonthsSchema(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    amount: float
    months: List[int]
    year: int
    paid: bool = True
    paid_date: Optional[datetime] = None
