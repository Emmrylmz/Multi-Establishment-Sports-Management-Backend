from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(str(v)):
            raise ValueError("Invalid objectid")
        return ObjectId(str(v))


class PaymentType(str, Enum):
    MONTHLY = "monthly"
    PRIVATE_LESSON = "private_lesson"
    STORE_PURCHASE = "store_purchase"
    OTHER = "other"
    EXPENSE = "expense"


class PaymentWith(str, Enum):
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_PAYMENT = "mobile_payment"
    OTHER = "other"


class Status(str, Enum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERPAID = "overpaid"
    OVERDUE = "overdue"


class Payment(BaseModel):
    _id: Optional[str] = Field(None, alias="id")
    user_id: str
    payment_type: PaymentType
    payment_with: PaymentWith
    due_date: datetime
    amount: float
    paid_amount: float = 0  # New field to track how much has been paid
    remaining_amount: float  # New field to track remaining amount
    status: Status
    created_at: datetime = Field(default_factory=datetime.now)
    month: int
    year: int
    paid_date: Optional[datetime]
    province: str = Field(..., example="Izmir")
    description: Optional[str]

    class Config:
        json_encoders = {ObjectId: str}


class SinglePayment(BaseModel):
    user_id: str
    amount: float
    due_date: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    month: int
    year: int
    province: str
    paid_amount: float = None
    payment_with: PaymentWith
    payment_type: PaymentType


class SingleUserPayment(BaseModel):
    user_id: str


class PrivateLessonResponseSchema(BaseModel):
    lesson_id: str
    status: str


class CreatePaymentForMonthsSchema(BaseModel):
    # id: Optional[str] = Field(None, alias="_id")
    user_id: str
    months_and_amounts: dict
    default_amount: float
    payment_with: PaymentWith
    year: int
    status: Optional[Status]
    paid_date: Optional[datetime] = None
    province: str = Field(..., example="Izmir")


class PaymentUpdateSchema(BaseModel):
    amount: Optional[float]
    paid_amount: Optional[float]
    due_date: Optional[datetime]
    status: Optional[Status]
    province: Optional[str]


class PaymentUpdateItem(BaseModel):
    id: str = Field(alias="_id")
    month: int
    paid_amount: float = Field(..., ge=0)
    payment_with: Optional[PaymentWith] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class PaymentUpdateList(BaseModel):
    year: int
    province: str
    user_id: str
    default_amount: float
    payments: List[PaymentUpdateItem]


class PaymentUpdateResponse(BaseModel):
    status: str
    message: str
    modified_count: int


class ExpenseCreate(BaseModel):
    user_id: str
    payment_with: PaymentWith
    due_date: Optional[datetime] = Field(default_factory=datetime.now)
    amount: float = Field(..., lt=0)  # Ensure amount is negative
    description: Optional[str]
    month: int = Field(..., ge=1, le=12)
    year: int
    province: str = Field(..., example="Izmir")

    class Config:
        json_encoders = {ObjectId: str}
