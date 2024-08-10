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
from .MongoDBService import MongoDBService
from ..celery_app.celery_tasks import update_monthly_balance, invalidate_caches


class PaymentService(MongoDBService):
    @classmethod
    async def initialize(cls, database, redis_client: RedisClient):
        self = cls.__new__(cls)
        await self.__init__(database, redis_client)
        return self

    async def __init__(self, database, redis_client: RedisClient):
        self.collection = await get_collection("Payment", database)
        self.balance_collection = await get_collection("Monthly_Balance", database)
        self.redis_client = redis_client
        await super().__init__(self.collection)

    async def get_user_data_by_year(self, user_id: str, year: int):
        cache_key = f"user_data_by_year:{user_id}:{year}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        query = {"user_id": user_id, "year": year}
        payments = await self.list(query)

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

        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"year": current_year, "month": {"$lt": current_month}},
                        {
                            "year": lookback_start_date.year,
                            "month": {"$gte": lookback_start_date.month},
                        },
                    ],
                    "document_type": "monthly_balance",
                    "province": province,
                }
            },
            {"$sort": {"year": 1, "month": 1}},
            {
                "$group": {
                    "_id": None,
                    "monthly_balances": {"$push": "$total_balance"},
                    "months_count": {"$sum": 1},
                    "first_month": {"$first": "$month"},
                    "first_year": {"$first": "$year"},
                    "last_month": {"$last": "$month"},
                    "last_year": {"$last": "$year"},
                }
            },
        ]

        result = await self.balance_collection.aggregate(pipeline).to_list(None)

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

        pipeline = [
            {"$match": match_condition},
            {
                "$group": {
                    "_id": "$province",
                    "total_earned": {"$sum": "$total_balance"},
                    "total_tickets": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "province": "$_id",
                    "total_earned": 1,
                    "total_tickets": 1,
                    "_id": 0,
                }
            },
            {"$sort": {"total_earned": -1}},
        ]

        results = await self.balance_collection.aggregate(pipeline).to_list(None)

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

    async def create_monthly_payments(
        self,
        payment_data: CreatePaymentForMonthsSchema,
    ):
        try:
            user_id = payment_data.user_id
            months_and_amounts = payment_data.months_and_amounts
            year = payment_data.year
            province = payment_data.province
            payment_with = payment_data.payment_with
            default_amount = payment_data.default_amount

            if not months_and_amounts or not year:
                raise ValueError("Months and amounts, and year must be provided")

            current_date = datetime.utcnow()
            sorted_months = sorted(int(month) for month in months_and_amounts.keys())

            create_operations = []
            balance_updates = {}
            result = None

            client = self.collection.database.client

            async with await client.start_session() as session:
                async with session.start_transaction():
                    for month in sorted_months:
                        paid_amount = months_and_amounts[str(month)]
                        due_date = datetime(year, month + 1, current_date.day)
                        remaining_amount = default_amount - paid_amount

                        status = self._determine_status(paid_amount, default_amount)

                        payment_data = {
                            "status": status,
                            "amount": default_amount,
                            "paid_amount": paid_amount,
                            "remaining_amount": remaining_amount,
                            "paid_date": current_date if paid_amount > 0 else None,
                            "payment_with": payment_with,
                            "due_date": due_date,
                            "province": province,
                            "user_id": user_id,
                            "year": year,
                            "month": month,
                            "payment_type": PaymentType.MONTHLY,
                            "created_at": current_date,
                        }

                        create_operations.append(InsertOne(payment_data))

                        if (year, month) not in balance_updates:
                            balance_updates[(year, month)] = 0
                        balance_updates[(year, month)] += paid_amount

                    if create_operations:
                        result = await self.collection.bulk_write(
                            create_operations, session=session
                        )

                    await self._handle_next_month_ticket(
                        user_id,
                        year,
                        max(sorted_months),
                        default_amount,
                        province,
                        payment_with,
                        session,
                    )

                await session.commit_transaction()

            for (year, month), amount in balance_updates.items():
                update_monthly_balance.delay(
                    year=year, month=month, province=province, amount_change=amount
                )

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

        except ValueError as ve:
            await session.abort_transaction()
            raise HTTPException(status_code=400, detail=str(ve))
        except BulkWriteError as bwe:
            await session.abort_transaction()
            raise HTTPException(status_code=400, detail="Error processing payments")
        except Exception as e:
            await session.abort_transaction()
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def update_monthly_payments(self, payment_updates: PaymentUpdateList):
        try:
            update_operations = []
            balance_updates = {}
            cache_keys = set()

            for update in payment_updates.payments:
                new_paid_amount = update.paid_amount
                new_remaining_amount = payment_updates.default_amount - new_paid_amount
                new_status = self._determine_status(
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

    def _determine_status(self, paid_amount, default_amount):
        if paid_amount > default_amount:
            return Status.OVERPAID
        elif paid_amount == default_amount:
            return Status.PAID
        elif paid_amount > 0:
            return Status.PARTIALLY_PAID
        else:
            return Status.PENDING

    async def _handle_next_month_ticket(
        self, user_id, year, last_month, default_amount, province, payment_with, session
    ):
        next_month = (last_month + 1) % 12
        next_year = year + 1 if next_month == 0 else year
        next_due_date = datetime(next_year, next_month + 1, 1)

        await self.collection.update_one(
            {
                "user_id": user_id,
                "year": next_year,
                "month": next_month,
                "payment_type": PaymentType.MONTHLY,
            },
            {
                "$setOnInsert": {
                    "status": Status.PENDING,
                    "payment_with": payment_with,
                    "due_date": next_due_date,
                    "amount": default_amount,
                    "paid_amount": 0,
                    "remaining_amount": default_amount,
                    "created_at": datetime.utcnow(),
                    "province": province,
                }
            },
            upsert=True,
            session=session,
        )

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
        created_payment = await self.create(payment_data.dict(exclude_unset=True))

        cache_keys = [
            f"user_data_by_year_{created_lesson['player_id']}_{now.year}",
            f"total_earned_{now.year}_{province}",
        ]
        invalidate_caches.delay(cache_keys)

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
            update_fields["status"] = self._determine_status(
                update_data["paid_amount"], update_data["amount"]
            )
            update_fields["remaining_amount"] = (
                update_fields["amount"] - update_fields["paid_amount"]
            )
            update_fields["updated_at"] = datetime.utcnow()
            if not update_fields:
                raise HTTPException(status_code=400, detail="No valid fields to update")

            # Perform the update
            result = await self.collection.find_one_and_update(
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
            result = await self.collection.delete_one({"_id": ObjectId(payment_id)})
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
                    "status": self._determine_status(
                        payment_dict["paid_amount"], payment_dict["amount"]
                    ),
                }
            )

            # Insert the payment into the database
            result = await self.collection.insert_one(payment_dict)

            if not result.inserted_id:
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
                "payment_id": str(result.inserted_id),
            }

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def enter_expenses(self, expense_payment: Payment):
        try:
            created_expense = await self.create(
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
