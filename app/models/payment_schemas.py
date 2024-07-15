from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum


class PaymentType(str, Enum):
    MONTHLY = "monthly"
    PRIVATE_LESSON = "private_lesson"


class Status(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class Payment(BaseModel):
    user_id: str
    payment_type: str
    due_date: datetime
    amount: float
    status: Status
    created_at: datetime
    month: int
    year: int
    paid_date: Optional[datetime]
    province: str = Field(..., example="Izmir")

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
    months_and_amounts: dict
    year: int
    status: Status
    paid_date: Optional[datetime] = None
    province: str = Field(..., example="Izmir")
