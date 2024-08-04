from bson import ObjectId
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from typing import List, Dict, Any
from bson.json_util import dumps, loads
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from ..models.payment_schemas import (
    Payment,
    CreatePaymentForMonthsSchema,
    PaymentUpdateList,
    PaymentType,
    Status,
    PaymentWith,
)
from ..redis_client import RedisClient
from ..database import get_collection
from .MongoDBService import MongoDBService


class PaymentService(MongoDBService):
    @classmethod
    async def initialize(cls, database, redis_client: RedisClient):
        self = cls.__new__(cls)
        await self.__init__(database, redis_client)
        return self

    async def __init__(self, database, redis_client: RedisClient):
        self.collection = await get_collection("Payment", database)
        self.balance_collection = await get_collection("Monthly_Balances", database)
        self.redis_client = redis_client
        await super().__init__(self.collection)

    async def update_monthly_balance(
        self, year: int, month: int, province: str, amount_change: float, session=None
    ):
        update_operation = {
            "$inc": {"total_balance": amount_change},
            "$set": {"last_updated": datetime.utcnow()},
        }
        if session:
            await self.balance_collection.update_one(
                {
                    "year": year,
                    "month": month,
                    "province": province,
                    "document_type": "monthly_balance",
                },
                update_operation,
                upsert=True,
                session=session,
            )
        else:
            await self.balance_collection.update_one(
                {
                    "year": year,
                    "month": month,
                    "province": province,
                    "document_type": "monthly_balance",
                },
                update_operation,
                upsert=True,
            )
        await self.invalidate_cache(f"monthly_balance:{year}:{month}:{province}")

    async def get_monthly_revenue(self, month: int, year: int):
        cache_key = f"monthly_revenue:{year}:{month}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        pipeline = [
            {"$match": {"month": month, "year": year, "status": Status.PAID}},
            {"$group": {"_id": None, "total_revenue": {"$sum": "$amount"}}},
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        total_revenue = result[0]["total_revenue"] if result else 0

        await self.redis_client.set(cache_key, dumps(total_revenue), expire=3600)
        return total_revenue

    async def get_annual_revenue(self, year: int):
        cache_key = f"annual_revenue:{year}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        pipeline = [
            {"$match": {"year": year, "status": Status.PAID}},
            {"$group": {"_id": None, "total_revenue": {"$sum": "$amount"}}},
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        total_revenue = result[0]["total_revenue"] if result else 0

        await self.redis_client.set(cache_key, dumps(total_revenue), expire=3600)
        return total_revenue

    async def get_revenue_by_month_range(
        self, year: int, start_month: int = 0, end_month: int = 11
    ):
        cache_key = f"revenue_by_month_range:{year}:{start_month}:{end_month}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return loads(cached_result)

        pipeline = [
            {
                "$match": {
                    "month": {"$gte": start_month, "$lte": end_month},
                    "year": year,
                    "status": Status.PAID,
                }
            },
            {"$group": {"_id": "$month", "revenue": {"$sum": "$amount"}}},
            {"$sort": {"_id": 1}},
            {
                "$group": {
                    "_id": None,
                    "months": {"$push": {"month": "$_id", "revenue": "$revenue"}},
                    "total": {"$sum": "$revenue"},
                }
            },
            {"$project": {"_id": 0, "months": 1, "total": 1}},
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        revenue_data = result[0] if result else {"months": [], "total": 0}

        await self.redis_client.set(cache_key, dumps(revenue_data), expire=3600)
        return revenue_data

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
            "earnings_by_province": results,
        }

        if province:
            response_content["province"] = province
            if results:
                response_content["earnings_by_province"] = results[0]
            else:
                response_content["earnings_by_province"] = {
                    "province": province,
                    "total_earned": 0,
                    "total_tickets": 0,
                }

        await self.redis_client.set(cache_key, dumps(response_content), expire=300)
        return response_content

    async def create_monthly_payments(self, payment_data: CreatePaymentForMonthsSchema):
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

                        for (year, month), amount in balance_updates.items():
                            await self.update_monthly_balance(
                                year, month, province, amount, session
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

            # Invalidate relevant caches
            await self.invalidate_multiple_caches(
                user_id, year, sorted_months, province
            )

            return {
                "status": "success",
                "message": f"Created payments for {len(sorted_months)} months and handled next month's ticket",
                "created_count": result.inserted_count if result else 0,
            }

        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except BulkWriteError as bwe:
            raise HTTPException(status_code=400, detail="Error processing payments")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def update_monthly_payments(self, payment_updates: PaymentUpdateList):
        try:
            client = self.collection.database.client
            async with await client.start_session() as session:
                async with session.start_transaction():
                    update_operations = []
                    balance_updates = {}

                    for update in payment_updates.payments:
                        existing_payment = await self.collection.find_one(
                            {"_id": ObjectId(update.id)}, session=session
                        )
                        if not existing_payment:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Payment with id {ObjectId(update.id)} not found",
                            )

                        old_paid_amount = existing_payment.get("paid_amount", 0)
                        new_paid_amount = update.paid_amount
                        amount_change = new_paid_amount - old_paid_amount

                        update_data = {
                            "paid_amount": new_paid_amount,
                            "remaining_amount": existing_payment["amount"]
                            - new_paid_amount,
                            "status": self._determine_status(
                                new_paid_amount, existing_payment["amount"]
                            ),
                            "updated_at": datetime.utcnow(),
                        }
                        if update.payment_with:
                            update_data["payment_with"] = update.payment_with.value

                        update_operations.append(
                            UpdateOne(
                                {"_id": ObjectId(update.id)}, {"$set": update_data}
                            )
                        )

                        year = existing_payment["year"]
                        month = existing_payment["month"]
                        province = existing_payment["province"]

                        balance_key = (year, month, province)
                        if balance_key not in balance_updates:
                            balance_updates[balance_key] = 0
                        balance_updates[balance_key] += amount_change

                    if update_operations:
                        result = await self.collection.bulk_write(
                            update_operations, session=session
                        )

                        for (
                            year,
                            month,
                            province,
                        ), amount_change in balance_updates.items():
                            await self.update_monthly_balance(
                                year, month, province, amount_change, session
                            )

                    await self.invalidate_multiple_caches_for_updates(
                        payment_updates.payments
                    )

                    return {
                        "status": "success",
                        "message": f"Updated {len(update_operations)} payments",
                        "modified_count": result.modified_count if result else 0,
                    }

        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except HTTPException:
            raise
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

        # Invalidate relevant caches
        await self.redis_client.delete(f"monthly_revenue_{now.month}_{now.year}")
        await self.redis_client.delete(f"annual_revenue_{now.year}")
        await self.redis_client.delete(
            f"revenue_by_month_range_{now.year}_{now.month}_{now.month}"
        )
        await self.redis_client.delete(
            f"user_data_by_year_{created_lesson['player_id']}_{now.year}"
        )
        await self.redis_client.delete(f"expected_yearly_revenue_{province}")
        await self.redis_client.delete(f"total_earned_{now.year}_{province}")

        return created_payment

    async def update_payment(self, payment_id: str, update_data: dict):
        old_payment = await self.collection.find_one({"_id": ObjectId(payment_id)})
        if not old_payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        update_fields = {}
        allowed_fields = ["amount", "due_date", "status", "province", "paid_amount"]
        for field in allowed_fields:
            if field in update_data:
                update_fields[field] = update_data[field]

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        old_paid_amount = old_payment.get("paid_amount", 0)
        new_paid_amount = update_fields.get("paid_amount", old_paid_amount)

        if "status" in update_fields:
            if update_fields["status"] == Status.PENDING:
                new_paid_amount = 0
            elif (
                old_payment["status"] == Status.PENDING
                and update_fields["status"] != Status.PENDING
            ):
                new_paid_amount = update_fields.get(
                    "paid_amount", old_payment["amount"]
                )

        amount_change = new_paid_amount - old_paid_amount
        update_fields["paid_amount"] = new_paid_amount

        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(payment_id)},
            {"$set": update_fields},
            return_document=True,
        )

        if not result:
            raise HTTPException(status_code=400, detail="Update failed")

        if amount_change != 0:
            await self.update_monthly_balance(
                result["year"], result["month"], result["province"], amount_change
            )

        if "status" in update_fields:
            await self._handle_payment_status_change(old_payment, result)

        # Invalidate relevant caches
        await self.redis_client.delete(
            f"monthly_revenue_{result['month']}_{result['year']}"
        )
        await self.redis_client.delete(f"annual_revenue_{result['year']}")
        await self.redis_client.delete(
            f"revenue_by_month_range_{result['year']}_{result['month']}_{result['month']}"
        )
        await self.redis_client.delete(
            f"user_data_by_year_{result['user_id']}_{result['year']}"
        )
        await self.redis_client.delete(f"expected_yearly_revenue_{result['province']}")
        await self.redis_client.delete(
            f"total_earned_{result['year']}_{result['province']}"
        )

        return result

    async def delete_payment(self, payment_id: str):
        payment = await self.collection.find_one({"_id": ObjectId(payment_id)})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        result = await self.collection.delete_one({"_id": ObjectId(payment_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=400, detail="Deletion failed")

        await self._handle_next_month_ticket(payment, is_deletion=True)

        # Invalidate relevant caches
        await self.redis_client.delete(
            f"monthly_revenue_{payment['month']}_{payment['year']}"
        )
        await self.redis_client.delete(f"annual_revenue_{payment['year']}")
        await self.redis_client.delete(
            f"revenue_by_month_range_{payment['year']}_{payment['month']}_{payment['month']}"
        )
        await self.redis_client.delete(
            f"user_data_by_year_{payment['user_id']}_{payment['year']}"
        )
        await self.redis_client.delete(f"expected_yearly_revenue_{payment['province']}")
        await self.redis_client.delete(
            f"total_earned_{payment['year']}_{payment['province']}"
        )

        return {"status": "success", "message": "Payment deleted successfully"}

    async def _handle_payment_status_change(self, old_payment: dict, new_payment: dict):
        if (
            old_payment["status"] != Status.PAID
            and new_payment["status"] == Status.PAID
        ):
            await self._handle_next_month_ticket(new_payment, create_next=True)
        elif (
            old_payment["status"] == Status.PAID
            and new_payment["status"] != Status.PAID
        ):
            await self._handle_next_month_ticket(new_payment, delete_next=True)

    async def make_single_payment(self, payment: Payment):
        payment_dict = payment.dict()
        if "_id" in payment_dict:
            payment_id = payment_dict.pop("_id")
            if not ObjectId.is_valid(payment_id):
                raise ValueError("Invalid _id format")

            payment_dict["updated_at"] = datetime.utcnow()

            existing_payment = await self.collection.find_one(
                {"_id": ObjectId(payment_id)}
            )
            if not existing_payment:
                raise ValueError(f"No payment found with id {payment_id}")

            amount_change = payment_dict.get("paid_amount", 0) - existing_payment.get(
                "paid_amount", 0
            )

            result = await self.collection.update_one(
                {"_id": ObjectId(payment_id)}, {"$set": payment_dict}
            )

            if result.modified_count == 0:
                raise ValueError(f"Failed to update payment with id {payment_id}")

            await self.update_monthly_balance(
                payment.year, payment.month, payment.province, amount_change
            )

            updated_payment = await self.collection.find_one(
                {"_id": ObjectId(payment_id)}
            )
            payment_result = Payment(**updated_payment)
        else:
            payment_dict["created_at"] = datetime.utcnow()
            payment_dict["updated_at"] = payment_dict["created_at"]

            result = await self.collection.insert_one(payment_dict)

            await self.update_monthly_balance(
                payment.year, payment.month, payment.province, payment.paid_amount
            )

            created_payment = await self.collection.find_one(
                {"_id": result.inserted_id}
            )
            payment_result = Payment(**created_payment)

        # Invalidate relevant caches
        await self.redis_client.delete(
            f"monthly_revenue_{payment.month}_{payment.year}"
        )
        await self.redis_client.delete(f"annual_revenue_{payment.year}")
        await self.redis_client.delete(
            f"revenue_by_month_range_{payment.year}_{payment.month}_{payment.month}"
        )
        await self.redis_client.delete(
            f"user_data_by_year_{payment.user_id}_{payment.year}"
        )
        await self.redis_client.delete(f"expected_yearly_revenue_{payment.province}")
        await self.redis_client.delete(
            f"total_earned_{payment.year}_{payment.province}"
        )

        return payment_result

    async def enter_expenses(self, expense_payment: Payment):
        try:
            client = self.collection.database.client
            async with await client.start_session() as session:
                async with session.start_transaction():
                    created_expense = await self.create(
                        expense_payment.dict(exclude_unset=True)
                    )

                    await self.update_monthly_balance(
                        expense_payment.year,
                        expense_payment.month,
                        expense_payment.province,
                        -abs(expense_payment.amount),
                        session,
                    )

            # Invalidate relevant caches
            await self.redis_client.delete(
                f"monthly_revenue_{expense_payment.month}_{expense_payment.year}"
            )
            await self.redis_client.delete(f"annual_revenue_{expense_payment.year}")
            await self.redis_client.delete(
                f"revenue_by_month_range_{expense_payment.year}_{expense_payment.month}_{expense_payment.month}"
            )
            await self.redis_client.delete(
                f"expected_yearly_revenue_{expense_payment.province}"
            )
            await self.redis_client.delete(
                f"total_earned_{expense_payment.year}_{expense_payment.province}"
            )

            return Payment(**created_expense)
        except ValidationError as ve:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while entering the expense: {str(e)}",
            )

    async def invalidate_multiple_caches(self, user_id, year, months, province):
        cache_keys = [f"monthly_revenue:{year}:{month}" for month in months] + [
            f"annual_revenue:{year}",
            f"revenue_by_month_range:{year}:{min(months)}:{max(months)}",
            f"user_data_by_year:{user_id}:{year}",
            f"expected_yearly_revenue:{province}",
            f"total_earned:{year}:{province}",
        ]
        await self.redis_client.delete(*cache_keys)

    async def invalidate_multiple_caches_for_updates(self, payment_updates):
        cache_keys = set()
        for update in payment_updates:
            existing_payment = await self.collection.find_one(
                {"_id": ObjectId(update.id)}
            )
            if existing_payment:
                cache_keys.update(
                    [
                        f"monthly_revenue:{existing_payment['year']}:{existing_payment['month']}",
                        f"annual_revenue:{existing_payment['year']}",
                        f"revenue_by_month_range:{existing_payment['year']}:{existing_payment['month']}:{existing_payment['month']}",
                        f"user_data_by_year:{existing_payment['user_id']}:{existing_payment['year']}",
                        f"expected_yearly_revenue:{existing_payment['province']}",
                        f"total_earned:{existing_payment['year']}:{existing_payment['province']}",
                    ]
                )
        await self.redis_client.delete(*cache_keys)
