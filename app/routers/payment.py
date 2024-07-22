from fastapi import APIRouter, status, Depends, HTTPException, Request
from ..tools.RabbitClient import RabbitClient
from ..tools.ExponentServerSDK import push_client, PushMessage
from ..models.payment_schemas import (
    Payment,
    SingleUserPayment,
    MonthlyRevenuePayloadSchema,
    YearlyRevenuePayloadSchema,
    RevenueByMonthRangePayloadSchema,
    PrivateLessonResponseSchema,
    CreatePaymentForMonthsSchema,
    PaymentUpdateSchema,
)
from .BaseRouter import BaseRouter, get_base_router
from typing import List
from ..oauth2 import require_user

router = APIRouter()


@router.get(
    "/{user_id}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def get_user_payments_by_id(
    user_id: str,
    base_router: BaseRouter = Depends(get_base_router),
):
    payments = await base_router.payment_controller.get_user_payments(user_id)
    if not payments:
        raise HTTPException(
            status_code=404, detail="User not found or no payments available"
        )
    return payments


@router.post("/create_payment_for_months", status_code=status.HTTP_201_CREATED)
async def pay_user_payment(
    payment: CreatePaymentForMonthsSchema,
    base_router: BaseRouter = Depends(get_base_router),
):
    success = await base_router.payment_controller.create_payment_for_months(payment)
    if not success:
        raise HTTPException(
            status_code=404, detail="Payment not found or could not be updated"
        )
    return {"status": "success"}


@router.post("/get_monthly_revenue", status_code=status.HTTP_200_OK)
async def get_monthly_revenue(
    payload: MonthlyRevenuePayloadSchema,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.get_monthly_revenue(
        month=payload.month, year=payload.year
    )


@router.post("/get_yearly_revenue", status_code=status.HTTP_200_OK)
async def get_monthly_revenue(
    payload: YearlyRevenuePayloadSchema,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.get_yearly_revenue(year=payload.year)


@router.post("/get_revenue_by_month_range", status_code=status.HTTP_200_OK)
async def get_monthly_revenue(
    payload: RevenueByMonthRangePayloadSchema,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.get_revenue_by_month_range(
        year=payload.year, start_month=payload.start_month, end_month=payload.end_month
    )


@router.post(
    "/private-lessons/{lesson_id}/pay", response_model=PrivateLessonResponseSchema
)
async def pay_private_lesson(
    lesson_id: str,
    request: Request,
    # user_id: str = Depends(require_user),
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.pay_private_lesson(
        lesson_id,
        request,
    )


@router.put("/update/{payment_id}")
async def update_payment(
    payment_id: str,
    update_data: PaymentUpdateSchema,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.update_payment(payment_id, update_data)


@router.delete("/delete/{payment_id}")
async def delete_payment(
    payment_id: str,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.delete_payment(payment_id)
