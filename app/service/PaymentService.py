# app/services/user_service.py
from fastapi import Depends, status, HTTPException
from typing import Optional, List, Dict
from .. import utils
from datetime import datetime
from bson import ObjectId
import logging
from ..config import settings
from .BaseService import get_base_service, BaseService
from ..database import get_collection
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorCollection
from ..service.MongoDBService import MongoDBService
from ..models.payment_schemas import (
    Payment,
    PaymentType,
    Status,
    CreatePaymentForMonthsSchema,
)
from dateutil.relativedelta import relativedelta


class PaymentService(MongoDBService):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def get_user_payments(self, user_id: str):
        payments_cursor = self.collection.find({"user_id": user_id})
        payments = await payments_cursor.to_list(length=None)  # Convert cursor to list
        return payments

    async def update_payment(self, user_id: str, month: int, year: int):
        result = await self.collection.update_one(
            {"user_id": user_id, "month": month, "year": year},
            {"$set": {"paid": True, "paid_date": datetime.utcnow()}},
        )
        return result.modified_count > 0

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
            player_id=created_lesson["user_id"],
            amount=created_lesson["lesson_fee"],
            payment_type=PaymentType.PRIVATE_LESSON,
            paid=has_paid,
            month=now.month,
            year=now.year,
            paid_date=datetime.utcnow() if has_paid else None,
            province=province,
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
