from fastapi import HTTPException, status
from bson import ObjectId
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any
from bson.json_util import dumps, loads
from pymongo import UpdateOne, InsertOne
from pymongo.errors import BulkWriteError
from ..models.payment_schemas import (
    Payment,
    CreatePaymentForMonthsSchema,
    PaymentUpdateList,
    PaymentType,
    Status,
    PaymentWith,
    SinglePayment,
)
from ..redis_client import RedisClient
from ..database import get_collection
from ..celery_app.celery_tasks import update_monthly_balance, invalidate_caches
from ..repositories.PaymentRepository import PaymentRepository


class PaymentService:
    @classmethod
    async def initialize(
        cls, payment_repository: PaymentRepository, redis_client: RedisClient
    ):
        self = cls.__new__(cls)
        await self.__init__(payment_repository, redis_client)
        return self

    async def __init__(
        self, payment_repository: PaymentRepository, redis_client: RedisClient
    ):
        self.payment_repository = payment_repository
        self.redis_client = redis_client

    async def get_user_data_by_year(self, user_id: str, year: int):
        cache_key = f"user_data_by_year:{user_id}:{year}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        payments = await self.payment_repository.payment_list_by_user_id_and_year(
            user_id=user_id, year=year
        )

        await self.redis_client.set(cache_key, dumps(payments), expire=3600)
        return payments

    async def get_expected_yearly_revenue(self, province: str, max_lookback_months=6):
        cache_key = f"expected_yearly_revenue_{province}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        current_date = datetime.utcnow()
        current_year = current_date.year
        current_month = current_date.month
        lookback_start_date = current_date - relativedelta(months=max_lookback_months)

        result = await self.payment_repository.expected_yearly_revenue_aggregation(
            current_date, current_year, current_month, lookback_start_date, province
        )

        if not result:
            return {
                "year": current_year,
                "expected_yearly_revenue": 0,
                "message": f"No data available for the lookback period in province {province}",
            }

        data = result[0]
        monthly_balances = data["monthly_balances"]
        months_count = data["months_count"]

        if months_count == 0:
            return {
                "year": current_year,
                "expected_yearly_revenue": 0,
                "message": f"No monthly balance data available for province {province}",
            }

        total_balance = sum(monthly_balances)
        average_monthly_balance = total_balance / months_count
        remaining_months = 12 - current_month + 1
        expected_yearly_revenue = total_balance + (
            average_monthly_balance * remaining_months
        )

        result = {
            "year": current_year,
            "expected_yearly_revenue": expected_yearly_revenue,
            "breakdown": {
                "average_monthly_balance": average_monthly_balance,
                "total_balance_so_far": total_balance,
                "months_of_data": months_count,
                "remaining_months": remaining_months,
                "lookback_period_start": f"{data['first_year']}-{data['first_month']:02d}",
                "lookback_period_end": f"{data['last_year']}-{data['last_month']:02d}",
            },
        }

        await self.redis_client.set(cache_key, dumps(result), expire=3600)
        return result

    async def get_total_earned_by_year_and_province(
        self, year: int, province: str = None
    ):
        cache_key = f"total_earned_{year}_{province}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        match_condition = {"year": year, "document_type": "monthly_balance"}
        if province:
            match_condition["province"] = province

        results = (
            await self.payment_repository.total_earned_by_year_and_province_aggregation(
                match_condition
            )
        )
        total_earned_overall = sum(result["total_earned"] for result in results)
        total_tickets_overall = sum(result["total_tickets"] for result in results)

        response_content = {
            "year": year,
            "total_earned_overall": total_earned_overall,
            "total_tickets_overall": total_tickets_overall,
        }

        if province:
            response_content["province"] = province

        await self.redis_client.set(cache_key, dumps(response_content), expire=3600)
        return response_content

    async def create_monthly_payments(self, payment_data: CreatePaymentForMonthsSchema):
        session: AsyncIOMotorClientSession = None
        try:
            user_id = payment_data.user_id
            months_and_amounts = payment_data.months_and_amounts
            year = payment_data.year
            province = payment_data.province
            payment_with = payment_data.payment_with
            default_amount = payment_data.default_amount

            current_date = datetime.utcnow()

            client = self.payment_repository.collection.database.client
            session = await client.start_session()

            async with session.start_transaction():
                create_operations, balance_updates, sorted_months = (
                    self.payment_repository._prepare_create_operations(
                        user_id,
                        months_and_amounts,
                        year,
                        province,
                        payment_with,
                        default_amount,
                        current_date,
                    )
                )

                if create_operations:
                    result = await self.payment_repository._execute_bulk_write(
                        create_operations, session
                    )

                    await self.payment_repository._handle_next_month_ticket(
                        user_id,
                        year,
                        max(sorted_months),
                        default_amount,
                        province,
                        payment_with,
                        session,
                    )

                for (year, month), amount in balance_updates.items():
                    update_monthly_balance.delay(
                        year=year, month=month, province=province, amount_change=amount
                    )
                else:
                    result = None

                # Transaction will be committed when exiting the context

            # Invalidate caches after the transaction commits
            cache_keys = [
                f"user_data_by_year:{user_id}:{year}",
                f"total_earned_{year}_{province}",
            ]
            invalidate_caches.delay(cache_keys)

            return {
                "status": "success",
                "message": f"Created payments for {len(sorted_months)} months and handled next month's ticket",
                "created_count": result.inserted_count if result else 0,
            }

        except HTTPException as http_exc:
            if session:
                await session.abort_transaction()
            raise http_exc
        # except BulkWriteError as bwe:
        #     if session:
        #         await session.abort_transaction()
        #     raise HTTPException(
        #         status_code=400, detail=f"Error processing payments: {str(bwe)}"
        #     )
        # except Exception as e:
        #     if session:
        #         await session.abort_transaction()
        #     raise HTTPException(
        #         status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        #     )
        finally:
            if session:
                await session.end_session()

    async def update_monthly_payments(self, payment_updates: PaymentUpdateList):
        try:
            update_operations = []
            balance_updates = {}
            cache_keys = set()

            for update in payment_updates.payments:
                new_paid_amount = update.paid_amount
                new_remaining_amount = payment_updates.default_amount - new_paid_amount
                new_status = self.payment_repository._determine_status(
                    new_paid_amount, payment_updates.default_amount
                )

                update_data = {
                    "$set": {
                        "paid_amount": new_paid_amount,
                        "remaining_amount": new_remaining_amount,
                        "status": new_status,
                        "updated_at": datetime.utcnow(),
                    }
                }

                if update.payment_with:
                    update_data["$set"]["payment_with"] = update.payment_with

                update_operations.append(
                    UpdateOne({"_id": ObjectId(update.id)}, update_data)
                )

                balance_key = (
                    payment_updates.year,
                    update.month,
                    payment_updates.province,
                )
                balance_updates[balance_key] = (
                    balance_updates.get(balance_key, 0) + new_paid_amount
                )

                cache_keys.add(
                    f"user_data_by_year:{payment_updates.user_id}:{payment_updates.year}"
                )
                cache_keys.add(
                    f"total_earned_{payment_updates.year}_{payment_updates.province}"
                )

            if update_operations:
                result = await self.collection.bulk_write(update_operations)

                if result.modified_count != len(update_operations):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Some updates failed. Expected {len(update_operations)} updates, but only {result.modified_count} succeeded.",
                    )

                for (year, month, province), amount_change in balance_updates.items():
                    update_monthly_balance.delay(year, month, province, amount_change)

            invalidate_caches.delay(list(cache_keys))

            return {
                "status": "success",
                "message": f"Updated {result.modified_count} payments",
                "modified_count": result.modified_count,
            }

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def update_monthly_payments(self, payment_updates: PaymentUpdateList):
        session: AsyncIOMotorClientSession = None
        try:
            # Start a client session
            session = (
                await self.payment_repository.collection.database.client.start_session()
            )

            async with session.start_transaction():
                update_operations, balance_updates, cache_keys = (
                    self.payment_repository._prepare_update_operations(payment_updates)
                )

                if update_operations:
                    result = await self.payment_repository._execute_bulk_write(
                        update_operations, session
                    )

                    modified_count = result.modified_count

                    # Perform balance updates within the transaction
                    for (
                        year,
                        month,
                        province,
                    ), amount_change in balance_updates.items():
                        update_monthly_balance.delay(
                            year, month, province, amount_change
                        )  # Commit the transaction (happens automatically when exiting the context)

                    response = {
                        "status": "success",
                        "message": f"Updated {modified_count} payments",
                        "modified_count": modified_count,
                    }

                else:
                    # No updates to perform
                    response = {
                        "status": "success",
                        "message": "No updates to perform",
                        "modified_count": 0,
                    }

            # Invalidate caches after transaction commits
            invalidate_caches.delay(list(cache_keys))

            return response

        except HTTPException as http_exc:
            # Re-raise HTTP exceptions
            raise http_exc
        except Exception as e:
            # Abort the transaction if any exception occurs
            if session:
                await session.abort_transaction()
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )
        finally:
            if session:
                await session.end_session()

    async def create_payment_for_private_lesson(
        self, created_lesson: dict, has_paid: bool, province: str
    ):
        now = datetime.utcnow()
        payment_data = Payment(
            user_id=created_lesson["player_id"],
            amount=created_lesson["lesson_fee"],
            payment_type=PaymentType.PRIVATE_LESSON,
            status=Status.PAID if has_paid else Status.PENDING,
            month=now.month,
            year=now.year,
            paid_date=datetime.utcnow() if has_paid else None,
            province=province,
            created_at=datetime.utcnow(),
            payment_with=PaymentWith.OTHER,
            due_date=now + relativedelta(months=1),
        )
        created_payment = await self.payment_repository.create_payment(
            payment_data.dict(exclude_unset=True)
        )

        return created_payment

    async def update_payment(self, payment_id: str, update_data: dict):
        try:
            # Define allowed fields for update
            allowed_fields = [
                "amount",
                "due_date",
                "status",
                "province",
                "paid_amount",
                "payment_with",
            ]

            # Filter update_data to only include allowed fields
            update_fields = {
                k: v for k, v in update_data.items() if k in allowed_fields
            }
            update_fields["status"] = self.payment_repository._determine_status(
                update_data["paid_amount"], update_data["amount"]
            )
            update_fields["remaining_amount"] = (
                update_fields["amount"] - update_fields["paid_amount"]
            )
            update_fields["updated_at"] = datetime.utcnow()

            # Perform the update
            result = await self.payment_repository.collection.find_one_and_update(
                {"_id": ObjectId(payment_id)},
                {"$set": update_fields},
                return_document=True,
            )

            if not result:
                raise HTTPException(
                    status_code=404, detail="Payment not found or update failed"
                )

            # Trigger cache invalidation
            cache_keys = [
                f"user_data_by_year_{result['user_id']}_{result['year']}",
                f"total_earned_{result['year']}_{result['province']}",
            ]
            invalidate_caches.delay(cache_keys)

            return result

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def delete_payment(self, payment_id: str):
        try:
            now = datetime.utcnow()
            result = await self.payment_repository.collection.delete_one(
                {"_id": ObjectId(payment_id)}
            )
            print(result.deleted_count)
            if result.deleted_count > 0:

                return {"status": "success", "message": "Payment deleted successfully"}
            elif result.deleted_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payment not found",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while deleting payment: {str(e)}",
            )

    async def make_single_payment(self, payment: SinglePayment):
        try:
            payment_dict = payment.dict()
            current_time = datetime.utcnow()

            # Update payment dictionary with calculated fields
            payment_dict.update(
                {
                    "paid_date": (
                        current_time if payment_dict["paid_amount"] > 0 else None
                    ),
                    "created_at": current_time,
                    "updated_at": current_time,
                    "remaining_amount": max(
                        0, payment_dict["amount"] - payment_dict["paid_amount"]
                    ),
                    "status": self.payment_repository._determine_status(
                        payment_dict["paid_amount"], payment_dict["amount"]
                    ),
                }
            )

            # Insert the payment into the database
            result = await self.payment_repository.create_payment(payment_dict)

            if not result["_id"]:
                raise HTTPException(status_code=400, detail="Failed to insert payment")

            # Trigger balance update
            update_monthly_balance.delay(
                payment_dict["year"],
                payment_dict["month"],
                payment_dict["province"],
                payment_dict["paid_amount"],
            )

            # Invalidate relevant caches
            cache_keys = [
                f"user_data_by_year:{payment_dict['user_id']}:{payment_dict['year']}",
                f"total_earned_{payment_dict['year']}_{payment_dict['province']}",
            ]
            invalidate_caches.delay(cache_keys)

            return {
                "status": "success",
                "message": "Payment created successfully",
                "payment_id": str(result["_id"]),
            }

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def enter_expenses(self, expense_payment: Payment):
        try:
            created_expense = await self.payment_repository.create_payment(
                expense_payment.dict(exclude_unset=True)
            )

            update_monthly_balance.delay(
                expense_payment.year,
                expense_payment.month,
                expense_payment.province,
                -abs(expense_payment.amount),
            )

            return Payment(**created_expense)
        except ValidationError as ve:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while entering the expense: {str(e)}",
            )
