from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
from typing import List, Dict, Optional, Any, Tuple, Set
from pymongo import UpdateOne, InsertOne
from pymongo.errors import BulkWriteError
from datetime import datetime
from ..database import get_collection
from ..models.payment_schemas import Payment, PaymentUpdateList, PaymentType, Status


class PaymentRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = None
        self.balance_collection = None

    @classmethod
    async def initialize(cls, database: AsyncIOMotorDatabase):
        self = cls(database)
        self.collection = await get_collection("Payment", database)
        self.balance_collection = await get_collection("Monthly_Balance", database)
        return self

    async def payment_list_by_user_id_and_year(self, user_id: str, year: int) -> list:
        cursor = self.collection.find({"user_id": user_id, "year": year})
        documents = await cursor.to_list(length=None)  # Fetch all documents from cursor
        return documents

    async def expected_yearly_revenue_aggregation(
        self, current_date, current_year, current_month, lookback_start_date, province
    ):
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

        return await self.balance_collection.aggregate(pipeline).to_list(length=None)

    async def total_earned_by_year_and_province_aggregation(
        self, match_condition: Dict[str, Any]
    ):
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

    def _determine_status(self, paid_amount, default_amount):
        if paid_amount > default_amount:
            return Status.OVERPAID
        elif paid_amount == default_amount:
            return Status.PAID
        elif paid_amount > 0:
            return Status.PARTIALLY_PAID
        else:
            return Status.PENDING

    def _prepare_create_operations(
        self,
        user_id: str,
        months_and_amounts: Dict[str, float],
        year: int,
        province: str,
        payment_with: str,
        default_amount: float,
        current_date: datetime,
    ) -> Tuple[List[InsertOne], Dict[Tuple[int, int, str], float], List[int]]:
        create_operations = []
        balance_updates = {}
        sorted_months = sorted(int(month) for month in months_and_amounts.keys())

        for month in sorted_months:
            paid_amount = months_and_amounts[str(month)]
            due_date = datetime(year, month + 1, current_date.day)
            remaining_amount = default_amount - paid_amount

            status = self._determine_status(paid_amount, default_amount)

            payment_record = {
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

            create_operations.append(InsertOne(payment_record))

            if (year, month) not in balance_updates:
                balance_updates[(year, month)] = 0
            balance_updates[(year, month)] += paid_amount

        return create_operations, balance_updates, sorted_months

    async def _execute_bulk_write(self, bw_operations: List, session) -> Any:
        try:
            result = await self.collection.bulk_write(bw_operations, session=session)
            return result
        except BulkWriteError as bwe:
            raise HTTPException(
                status_code=400, detail=f"Bulk write error: {str(bwe.details)}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Bulk write failed: {str(e)}")

    def _prepare_update_operations(
        self, payment_updates: PaymentUpdateList
    ) -> Tuple[List[UpdateOne], Dict[Tuple[int, int, str], float], Set[str]]:
        update_operations = []
        balance_updates = {}
        cache_keys = set()

        # Precompute cache keys
        cache_keys.add(
            f"user_data_by_year:{payment_updates.user_id}:{payment_updates.year}"
        )
        cache_keys.add(
            f"total_earned_{payment_updates.year}_{payment_updates.province}"
        )

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

            balance_key = (payment_updates.year, update.month, payment_updates.province)
            balance_updates[balance_key] = (
                balance_updates.get(balance_key, 0) + new_paid_amount
            )

        return update_operations, balance_updates, cache_keys

    async def create_payment(self, payment_dict: Dict[str, Any]):
        try:
            result = await self.collection.insert_one(payment_dict)
            payment_dict["_id"] = str(result.inserted_id)
            return payment_dict
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred while creating private lesson payment: {str(e)}",
            )
