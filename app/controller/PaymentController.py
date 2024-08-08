from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from pydantic import BaseModel, ValidationError
from bson import ObjectId
from ..oauth2 import require_user
from ..service import PaymentService, AuthService, UserService
from datetime import datetime
from ..models.payment_schemas import (
    PaymentType,
    PrivateLessonResponseSchema,
    Payment,
    Status,
    CreatePaymentForMonthsSchema,
    PaymentUpdateList,
    PaymentUpdateSchema,
    ExpenseCreate,
    SinglePayment,
)
from dateutil.relativedelta import relativedelta


class PaymentController:
    @classmethod
    async def create(
        cls,
        payment_service: PaymentService,
        user_service: UserService,
    ):
        self = cls.__new__(cls)
        await self.__init__(payment_service, user_service)
        return self

    def __init__(
        self,
        payment_service: PaymentService,
        user_service: UserService,
    ):
        self.payment_service = payment_service
        self.user_service = user_service

    # async def get_user_payments(self, user_id: str):
    #     payments = await self.payment_service.get_user_payments(user_id)
    #     return payments

    async def create_payment_for_months(self, payment: CreatePaymentForMonthsSchema):
        return await self.payment_service.create_monthly_payments(payment)

    async def update_payments_for_months(self, payment: PaymentUpdateList):
        return await self.payment_service.update_monthly_payments(payment)

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

    async def get_user_data_by_year(self, user_id: str, year: int):
        try:
            result = await self.payment_service.get_user_data_by_year(user_id, year)
            if result:
                return result
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def make_single_payment(self, payment: SinglePayment):
        try:
            result = await self.payment_service.make_single_payment(payment)
            if result:
                return result
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_team_payments(self, team_id: str):
        try:
            team = await self.team_service.get_by_id(team_id)
            if team:
                players = team["team_players"]
                payments = self.payment_service.get_player_payments(players)
                return payments
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def calculate_expected_revenue(self, province: str):
        return await self.payment_service.get_expected_yearly_revenue(province)

    async def get_total_earned_by_year_and_province(self, year: int, province: str):
        return await self.payment_service.get_total_earned_by_year_and_province(
            year, province
        )

    async def enter_expenses(self, expense: ExpenseCreate):
        try:
            payment_data = Payment(
                user_id=expense.user_id,
                payment_type=PaymentType.EXPENSE,
                payment_with=expense.payment_with,
                due_date=expense.due_date,
                amount=-abs(expense.amount),
                paid_amount=-abs(expense.amount),
                remaining_amount=0,
                status=Status.PAID,
                created_at=datetime.now(),
                month=expense.month,
                year=expense.year,
                paid_date=datetime.now(),
                province=expense.province,
                description=expense.description,
            )
        except ValidationError as ve:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

        try:
            result = await self.payment_service.enter_expenses(payment_data)
            return result
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
