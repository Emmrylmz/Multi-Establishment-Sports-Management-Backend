from fastapi import APIRouter, status, Depends, HTTPException, Request, Query
from ..rabbit_client.client import RabbitClient
from ..models.payment_schemas import (
    Payment,
    SingleUserPayment,
    MonthlyRevenuePayloadSchema,
    YearlyRevenuePayloadSchema,
    RevenueByMonthRangePayloadSchema,
    PrivateLessonResponseSchema,
    CreatePaymentForMonthsSchema,
    PaymentUpdateSchema,
    PaymentUpdateList,
    ExpenseCreate,
)
from typing import List, Optional
from ..oauth2 import require_user
import logging
from ..controller.PaymentController import PaymentController
from ..dependencies.controller_dependencies import get_payment_controller

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create_payment_for_months", status_code=status.HTTP_201_CREATED)
async def pay_user_payment(
    payment: CreatePaymentForMonthsSchema,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    success = await payment_controller.create_payment_for_months(payment)
    if not success:
        raise HTTPException(
            status_code=404, detail="Payment not found or could not be updated"
        )
    return success


@router.post("/update_payment_for_months", status_code=status.HTTP_201_CREATED)
async def pay_user_payment(
    payment: PaymentUpdateList,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    success = await payment_controller.update_payments_for_months(payment)
    if not success:
        raise HTTPException(
            status_code=404, detail="Payment not found or could not be updated"
        )
    return success


@router.put("/update/{payment_id}")
async def update_payment(
    payment_id: str,
    update_data: PaymentUpdateSchema,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    return await payment_controller.update_payment(payment_id, update_data)


@router.delete("/delete/{payment_id}")
async def delete_payment(
    payment_id: str,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    return await payment_controller.delete_payment(payment_id)


@router.get("/{user_id}/{year}")
async def get_user_data_by_year(
    user_id: str,
    year: int,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    return await payment_controller.get_user_data_by_year(user_id, year)


@router.post("/make_single_payment")
async def make_single_payment(
    payment: Payment,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    return await payment_controller.make_single_payment(payment)


@router.get("/get_team_payments/{team_id}")
async def get_team_payments(
    team_id: str,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    return await payment_controller.get_team_payments(team_id)


@router.get("/expected_revenue", status_code=status.HTTP_200_OK)
async def get_expected_revenue(
    province: str = Query(
        ..., description="The province for which to calculate revenue"
    ),
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    return await payment_controller.calculate_expected_revenue(province)


@router.get("/get_total_earned/{province}/{year}", status_code=status.HTTP_200_OK)
async def get_total_earned(
    year: int,
    province: Optional[str] = None,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    return await payment_controller.get_total_earned_by_year_and_province(
        year, province
    )


@router.post("/expenses/enter", status_code=status.HTTP_201_CREATED)
async def enter_expenses(
    expenses: ExpenseCreate,
    payment_controller: PaymentController = Depends(get_payment_controller),
):
    logger.info(f"Received expense creation request: {expenses}")
    try:
        result = await payment_controller.enter_expenses(expenses)
        logger.info(f"Expense created successfully: {result}")
        return result
    except HTTPException as http_exc:
        logger.error(f"HTTP exception in enter_expenses: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in enter_expenses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
