# app/services/user_service.py
from fastapi import Depends, status, HTTPException
from typing import Optional, List, Dict
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from ..database import get_collection
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection
from ..service.MongoDBService import MongoDBService
from ..models.payment_schemas import (
    Payment,
    PaymentType,
    Status,
    CreatePaymentForMonthsSchema,
    PaymentWith,
)
from dateutil.relativedelta import relativedelta
from pymongo import UpdateOne, InsertOne
from enum import Enum


class PaymentService(MongoDBService):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def create_payment_for_months(self, payment: CreatePaymentForMonthsSchema):
        user_id = payment.user_id
        months_and_amounts = payment.months_and_amounts
        year = payment.year
        province = payment.province
        payment_with = payment.payment_with
        status = payment.status
        paid_date = payment.paid_date
        default_amount = payment.default_amount

        if not months_and_amounts or not year:
            raise ValueError("Months and amounts, and year must be provided")

        current_date = datetime.utcnow()
        sorted_months = sorted(int(month) for month in months_and_amounts.keys())

        bulk_operations = []

        for month in sorted_months:
            amount = months_and_amounts[str(month)]
            due_date = datetime(
                year, month + 1, 1
            )  # Adding 1 to month for correct date

            bulk_operations.append(
                UpdateOne(
                    {
                        "user_id": user_id,
                        "year": year,
                        "month": month,
                        "payment_type": PaymentType.MONTHLY,
                    },
                    {
                        "$set": {
                            "status": status,
                            "amount": amount,
                            "paid_date": paid_date if status == Status.PAID else None,
                            "payment_with": payment_with,
                            "due_date": due_date,
                            "province": province,
                        },
                        "$setOnInsert": {
                            "created_at": current_date,
                        },
                    },
                    upsert=True,
                )
            )

        # Handle next month's ticket only if the current payments are PAID
        if status == Status.PAID:
            next_month = (max(sorted_months) + 1) % 12
            next_year = year + (1 if next_month == 0 else 0)
            next_due_date = datetime(next_year, next_month + 1, 1)

            bulk_operations.append(
                UpdateOne(
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
                            "created_at": current_date,
                            "province": province,
                        }
                    },
                    upsert=True,
                )
            )

        try:
            result = await self.collection.bulk_write(bulk_operations)
        except BulkWriteError as bwe:
            print(bwe.details)
            raise HTTPException(status_code=400, detail="Error processing payments")

        return {
            "status": "success",
            "message": f"Processed payments for {len(sorted_months)} months and handled next month's ticket",
            "processed_months": sorted_months,
            "next_month_ticket": (
                {
                    "month": next_month,
                    "year": next_year,
                    "amount": default_amount,
                }
                if status == Status.PAID
                else None
            ),
            "modified_count": result.modified_count,
            "upserted_count": result.upserted_count,
        }

    async def get_monthly_revenue(self, month: int, year: int):
        pipeline = [
            {"$match": {"month": month, "year": year, "paid": True}},
            {"$group": {"_id": None, "total_revenue": {"$sum": "$amount"}}},
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        if result:
            return result[0]["total_revenue"]
        return 0

    async def get_annual_revenue(self, year: int):
        pipeline = [
            {"$match": {"year": year, "paid": True}},
            {"$group": {"_id": None, "total_revenue": {"$sum": "$amount"}}},
        ]
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        if result:
            return result[0]["total_revenue"]
        return 0

    async def get_revenue_by_month_range(
        self, year: int, start_month: int = 0, end_month: int = 11
    ):
        pipeline = [
            {
                "$match": {
                    "month": {"$gte": start_month, "$lte": end_month},
                    "year": year,
                    "paid": True,
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
        if result:
            return result[0]
        return {"months": [], "total": 0}

    async def get_revenue_by_year_range(start_year: int, end_year: int):
        total_revenue = await self.collection.count_documents(
            {"year": {"$gte": start_year, "$lte": end_year}, "paid": True}
        )
        return total_revenue

    async def get_team_payments(team_id: str):
        payments_cursor = self.collection.find({"team_id": team_id})
        payments = [Payment(**payment) async for payment in payments_cursor]
        return payments

    async def get_payment_ratio(team_id: str):
        total_payments = await self.collection.count_documents({"team_id": team_id})
        paid_payments = await self.collection.count_documents(
            {"team_id": team_id, "paid": True}
        )
        if total_payments == 0:
            return 0
        return paid_payments / total_payments

    async def get_unpaid_players(team_id: str):
        unpaid_cursor = self.collection.find({"team_id": team_id, "paid": False})
        unpaid_players = [Payment(**payment) async for payment in unpaid_cursor]
        return unpaid_players

    async def create_payments(self, payments: list):
        result = await self.collection.insert_many(payments)
        return result.inserted_ids

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

        return created_payment

    async def pay_for_private_lesson(self, lesson_id: str):
        result = await self.collection.update_one(
            {"_id": lesson_id},
            {"$set": {"paid": True, "paid_date": datetime.utcnow()}},
        )
        return result.modified_count > 0

    async def get_unpaid_ticket(self, user_id: str) -> Optional[Payment]:
        """
        Retrieve the most recent unpaid ticket for a user.

        :param user_id: The ID of the user
        :return: The most recent unpaid Payment object, or None if no unpaid tickets
        """
        unpaid_ticket = await self.collection.find_one(
            {
                "user_id": user_id,
                "status": Status.PENDING,
                "payment_type": PaymentType.MONTHLY,
                "due_date": {
                    "$lt": datetime.utcnow()
                },  # Only get tickets that are past due
            },
            sort=[("due_date", -1)],
        )  # Sort by due_date descending to get the most recent

        return Payment(**unpaid_ticket) if unpaid_ticket else None

    async def pay_unpaid_ticket(self, ticket_id: str, amount: float) -> bool:
        """
        Pay for an unpaid ticket.

        :param ticket_id: The ID of the ticket to pay
        :param amount: The amount to pay
        :return: True if the payment was successful, False otherwise
        """
        result = await self.collection.update_one(
            {"_id": ticket_id, "status": Status.PENDING},
            {
                "$set": {
                    "status": Status.PAID,
                    "paid_date": datetime.utcnow(),
                    "amount": amount,
                }
            },
        )

        return result.modified_count > 0

    async def create_payments(self, payments: List[Payment]) -> List[str]:
        """
        Create multiple payments in the database.

        :param payments: List of Payment objects to create
        :return: List of inserted payment IDs
        """
        result = await self.collection.insert_many(
            [payment.dict() for payment in payments]
        )
        return result.inserted_ids

    async def _handle_unpaid_ticket(
        self, user_id: str, months_and_amounts: Dict[int, float]
    ) -> Dict[int, float]:
        unpaid_ticket = await self.get_unpaid_ticket(user_id)
        if unpaid_ticket:
            unpaid_month = unpaid_ticket.due_date.month - 1  # Convert to 0-indexed
            if unpaid_month in months_and_amounts:
                await self.pay_unpaid_ticket(
                    unpaid_ticket.id, months_and_amounts[unpaid_month]
                )
                del months_and_amounts[unpaid_month]
        return months_and_amounts

    def _create_paid_payments(
        self,
        user_id: str,
        months_and_amounts: Dict[int, float],
        year: int,
        province: str,
        current_date: datetime,
    ) -> List[Payment]:
        paid_payments = []
        for month_str, amount in months_and_amounts.items():
            month = int(month_str)  # Ensure month is an integer
            due_date = datetime(year, 1, 1) + relativedelta(months=month)
            payment_data = Payment(
                user_id=user_id,
                payment_type=PaymentType.MONTHLY,
                due_date=due_date,
                amount=amount,
                status=Status.PAID,
                created_at=current_date,
                month=month,
                year=year,
                paid_date=current_date,
                province=province,
            )
            paid_payments.append(payment_data)
        return paid_payments

    def _create_pending_payment(
        self,
        user_id: str,
        months_and_amounts: Dict[str, float],
        year: int,
        province: str,
        current_date: datetime,
    ) -> Payment:
        last_paid_month = max(int(m) for m in months_and_amounts.keys())
        next_month = (last_paid_month + 1) % 12
        next_year = year + (last_paid_month + 1) // 12
        pending_due_date = datetime(year, 1, 1) + relativedelta(
            months=last_paid_month + 1
        )
        pending_amount = months_and_amounts[str(last_paid_month)]

        return Payment(
            user_id=user_id,
            payment_type=PaymentType.MONTHLY,
            due_date=pending_due_date,
            amount=pending_amount,
            status=Status.PENDING,
            paid_date=None,
            month=next_month,
            year=next_year,
            created_at=current_date,
            province=province,
        )

    async def get_user_payments(self, user_id: str):
        payments = self.collection.find({"user_id": user_id})
        list = await payments.to_list(length=None)
        return list

    async def update_payment(self, payment_id: str, update_data: dict):
        # Ensure the payment exists
        payment = await self.collection.find_one({"_id": ObjectId(payment_id)})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # Prepare update data
        update_fields = {}
        allowed_fields = ["amount", "due_date", "status", "province"]
        for field in allowed_fields:
            if field in update_data:
                update_fields[field] = update_data[field]

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Perform the update
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(payment_id)},
            {"$set": update_fields},
            return_document=True,
        )

        if not result:
            raise HTTPException(status_code=400, detail="Update failed")

        # Handle the next month's ticket if status changed to or from 'paid'
        if "status" in update_fields:
            await self._handle_payment_status_change(payment, result)

        return result

    async def delete_payment(self, payment_id: str):
        # Ensure the payment exists
        payment = await self.collection.find_one({"_id": ObjectId(payment_id)})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # Perform the deletion
        result = await self.collection.delete_one({"_id": ObjectId(payment_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=400, detail="Deletion failed")

        # Handle the next month's ticket
        await self._handle_next_month_ticket(payment, is_deletion=True)

        return {"status": "success", "message": "Payment deleted successfully"}

    async def _handle_payment_status_change(self, old_payment: dict, new_payment: dict):
        if (
            old_payment["status"] != Status.PAID
            and new_payment["status"] == Status.PAID
        ):
            # Payment changed from not paid to paid
            await self._handle_next_month_ticket(new_payment, create_next=True)
        elif (
            old_payment["status"] == Status.PAID
            and new_payment["status"] != Status.PAID
        ):
            # Payment changed from paid to not paid
            await self._handle_next_month_ticket(new_payment, delete_next=True)

    async def _handle_next_month_ticket(
        self, payment: dict, create_next: bool = False, delete_next: bool = False
    ):
        next_month = (payment["month"] + 1) % 12
        next_year = payment["year"] + (1 if next_month == 0 else 0)

        # Find the ticket for the next month
        next_ticket = await self.collection.find_one(
            {
                "user_id": payment["user_id"],
                "month": next_month,
                "year": next_year,
                "payment_type": PaymentType.MONTHLY,
            }
        )

        if delete_next and next_ticket:
            # Delete the next month's ticket if it exists and delete_next is True
            await self.collection.delete_one({"_id": next_ticket["_id"]})
        elif create_next:
            if next_ticket:
                # Update the existing next month's ticket
                update_data = {
                    "amount": payment["amount"],
                    "province": payment["province"],
                    "status": Status.PENDING,
                }
                await self.collection.update_one(
                    {"_id": next_ticket["_id"]}, {"$set": update_data}
                )
            else:
                # Create a new ticket for the next month
                new_ticket = Payment(
                    user_id=payment["user_id"],
                    payment_type=PaymentType.MONTHLY,
                    due_date=datetime(
                        next_year, next_month + 1, 1
                    ),  # First day of next month
                    amount=payment["amount"],
                    status=Status.PENDING,
                    month=next_month,
                    year=next_year,
                    created_at=datetime.utcnow(),
                    province=payment["province"],
                )
                await self.collection.insert_one(new_ticket.dict())

    async def get_user_data_by_year(self, user_id: str, year: int):
        query = {"user_id": user_id, "year": year}
        payments = await self.list(query)
        return payments

    async def make_single_payment(self, payment: Payment):
        payment_dict = payment.dict()
        if "_id" in payment_dict:
            # Update existing payment
            payment_id = payment_dict.pop("_id")

            # Ensure _id is a valid ObjectId
            if not ObjectId.is_valid(payment_id):
                raise ValueError("Invalid _id format")

            payment_dict["updated_at"] = datetime.utcnow()

            result = await self.collection.update_one(
                {"_id": ObjectId(payment_id)}, {"$set": payment_dict}
            )

            if result.modified_count == 0:
                raise ValueError(f"No payment found with id {payment_id}")

            updated_payment = await self.collection.find_one(
                {"_id": ObjectId(payment_id)}
            )
            return Payment(**updated_payment)
        else:
            # Create new payment
            payment_dict["created_at"] = datetime.utcnow()
            payment_dict["updated_at"] = payment_dict["created_at"]

            result = await self.collection.insert_one(payment_dict)

            created_payment = await self.collection.find_one(
                {"_id": result.inserted_id}
            )
            return Payment(**created_payment)
