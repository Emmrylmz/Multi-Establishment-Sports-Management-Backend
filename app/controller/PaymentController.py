from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel
from bson import ObjectId
from .BaseController import BaseController
from ..oauth2 import require_user
from ..service import PaymentService, AuthService, UserService
from datetime import datetime
from ..models.payment_schemas import (
    PaymentType,
    PrivateLessonResponseSchema,
    Payment,
    Status,
    CreatePaymentForMonthsSchema,
    PaymentUpdateSchema,
)
from dateutil.relativedelta import relativedelta


class PaymentController(BaseController):
    def __init__(self, payment_service: PaymentService, user_service: UserService):
        super().__init__()  # Initialize the BaseController
        self.payment_service = payment_service
        self.user_service = user_service

    async def get_user_payments(self, user_id: str):
        payments = await self.payment_service.get_user_payments(user_id)
        return payments

    async def update_payment(self, user_id: str, month: int, year: int):
        return await self.payment_service.update_payment(user_id, month, year)

    async def create_payment_for_months(self, payment: CreatePaymentForMonthsSchema):
        return await self.payment_service.create_payment_for_months(payment)

    async def get_monthly_revenue(self, month: int, year: int):
        return await self.payment_service.get_monthly_revenue(month, year)

    async def get_yearly_revenue(self, year: int):
        return await self.payment_service.get_annual_revenue(year)

    async def get_revenue_by_month_range(
        self, year: int, start_month: int = 0, end_month: int = 11
    ):
        return await self.payment_service.get_revenue_by_month_range(
            year=year, start_month=start_month, end_month=end_month
        )

    async def pay_private_lesson(
        self,
        lesson_id: str,
        request: Request,
    ):
        # Validate the lesson exists and belongs to this user
        lesson = await self.payment_service.get_by_id(lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Private lesson not found")

        # if lesson["student_id"] != user_id:
        #     raise HTTPException(
        #         status_code=403, detail="Not authorized to pay for this lesson"
        #     )

        if lesson["paid"] == True:
            raise HTTPException(
                status_code=400, detail="This lesson has already been paid"
            )

        # Here you would typically integrate with a payment provider
        # For this example, we'll just update the status

        updated_lesson = await self.payment_service.pay_for_private_lesson(
            self.format_handler(lesson_id)
        )
        if not updated_lesson:
            raise HTTPException(
                status_code=500, detail="Failed to update payment status"
            )

        # Publish a message about the payment
        await request.app.rabbit_client.publish_message(
            routing_key="private_lesson.paid",
            message={"lesson": updated_lesson, "action": "paid"},
        )

        return PrivateLessonResponseSchema(lesson_id=lesson_id, status="paid")

    async def update_payment(self, payment_id: str, update_data: PaymentUpdateSchema):
        try:
            updated_payment = await self.payment_service.update_payment(
                payment_id, update_data.dict(exclude_unset=True)
            )
            return {
                "status": "success",
                "message": "Payment updated successfully",
                "payment": updated_payment,
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_payment(self, payment_id: str):
        try:
            result = await self.payment_service.delete_payment(payment_id)
            return result
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
