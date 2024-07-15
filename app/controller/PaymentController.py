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
)
from dateutil.relativedelta import relativedelta


class PaymentController(BaseController):
    def __init__(self, payment_service: PaymentService):
        super().__init__()  # Initialize the BaseController
        self.payment_service = payment_service

    async def get_user_payments(self, user_id: str):
        payments = await self.payment_service.get_user_payments(user_id)
        return payments

    async def update_payment(self, user_id: str, month: int, year: int):
        return await self.payment_service.update_payment(user_id, month, year)

    async def create_payment_for_months(self, payment: CreatePaymentForMonthsSchema):
        user_id = payment.user_id
        months_and_amounts = payment.months_and_amounts
        year = payment.year
        province = payment.province

        if not months_and_amounts or not year:
            raise ValueError("Months and amounts, and year must be provided")

        current_date = datetime.utcnow()

        months_and_amounts = await self.payment_service._handle_unpaid_ticket(
            user_id, months_and_amounts
        )
        paid_payments = self.payment_service._create_paid_payments(
            user_id, months_and_amounts, year, province, current_date
        )
        pending_payment = self.payment_service._create_pending_payment(
            user_id, months_and_amounts, year, province, current_date
        )

        all_payments = paid_payments + [pending_payment]
        inserted_ids = await self.payment_service.create_payments(all_payments)

        return {
            "status": "success",
            "message": f"Created {len(paid_payments)} paid payments and 1 pending payment",
            "inserted_ids": inserted_ids,
            "unpaid_ticket_paid": bool(
                await self.payment_service.get_unpaid_ticket(user_id)
            ),
        }

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
