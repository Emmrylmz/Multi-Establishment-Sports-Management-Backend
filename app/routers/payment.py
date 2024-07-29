from fastapi import APIRouter, status, Depends, HTTPException, Request, Query
from ..rabbit_client.client import RabbitClient
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
    PaymentUpdateList,
    ExpenseCreate,
)
from .BaseRouter import BaseRouter, get_base_router
from typing import List, Optional
from ..oauth2 import require_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# @router.get(
#     "/{user_id}",
#     status_code=status.HTTP_202_ACCEPTED,
# )
# async def get_user_payments_by_id(
#     user_id: str,
#     base_router: BaseRouter = Depends(get_base_router),
# ):
#     payments = await base_router.payment_controller.get_user_payments(user_id)
#     if not payments:
#         raise HTTPException(
#             status_code=404, detail="User not found or no payments available"
#         )
#     return payments


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
    return success


@router.post("/update_payment_for_months", status_code=status.HTTP_201_CREATED)
async def pay_user_payment(
    payment: PaymentUpdateList,
    base_router: BaseRouter = Depends(get_base_router),
):
    success = await base_router.payment_controller.update_payments_for_months(payment)
    if not success:
        raise HTTPException(
            status_code=404, detail="Payment not found or could not be updated"
        )
    return success


# @router.post("/get_monthly_revenue", status_code=status.HTTP_200_OK)
# async def get_monthly_revenue(
#     payload: MonthlyRevenuePayloadSchema,
#     base_router: BaseRouter = Depends(get_base_router),
# ):
#     return await base_router.payment_controller.get_monthly_revenue(
#         month=payload.month, year=payload.year
#     )


# @router.post("/get_yearly_revenue", status_code=status.HTTP_200_OK)
# async def get_yearly_revenue(
#     payload: YearlyRevenuePayloadSchema,
#     base_router: BaseRouter = Depends(get_base_router),
# ):
#     return await base_router.payment_controller.get_yearly_revenue(year=payload.year)


# @router.post("/get_revenue_by_month_range", status_code=status.HTTP_200_OK)
# async def get_monthly_revenue(
#     payload: RevenueByMonthRangePayloadSchema,
#     base_router: BaseRouter = Depends(get_base_router),
# ):
#     return await base_router.payment_controller.get_revenue_by_month_range(
#         year=payload.year, start_month=payload.start_month, end_month=payload.end_month
#     )


# @router.post(
#     "/private-lessons/{lesson_id}/pay", response_model=PrivateLessonResponseSchema
# )
# async def pay_private_lesson(
#     lesson_id: str,
#     request: Request,
#     # user_id: str = Depends(require_user),
#     base_router: BaseRouter = Depends(get_base_router),
# ):
#     return await base_router.payment_controller.pay_private_lesson(
#         lesson_id,
#         request,
#     )


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


@router.get("/{user_id}/{year}")
async def get_user_data_by_year(
    user_id: str, year: int, base_router: BaseRouter = Depends(get_base_router)
):
    return await base_router.payment_controller.get_user_data_by_year(user_id, year)


@router.post("/make_single_payment")
async def make_single_payment(
    payment: Payment, base_router: BaseRouter = Depends(get_base_router)
):
    return await base_router.payment_controller.make_single_payment(payment)


@router.get("/get_team_payments/{team_id}")
async def get_team_payments(
    team_id: str, base_router: BaseRouter = Depends(get_base_router)
):
    return await base_router.payment_controller.get_team_payments(team_id)


@router.get("/expected_revenue", status_code=status.HTTP_200_OK)
async def get_expected_revenue(
    province: str = Query(
        ..., description="The province for which to calculate revenue"
    ),
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.calculate_expected_revenue(province)


@router.get("/get_total_earned/{province}/{year}", status_code=status.HTTP_200_OK)
async def get_total_earned(
    year: int,
    province: Optional[str] = None,
    base_router: BaseRouter = Depends(get_base_router),
):
    return await base_router.payment_controller.get_total_earned_by_year_and_province(
        year, province
    )


@router.post("/expenses/enter", status_code=status.HTTP_201_CREATED)
async def enter_expenses(
    expenses: ExpenseCreate, base_router: BaseRouter = Depends(get_base_router)
):
    logger.info(f"Received expense creation request: {expenses}")
    try:
        result = await base_router.payment_controller.enter_expenses(expenses)
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
