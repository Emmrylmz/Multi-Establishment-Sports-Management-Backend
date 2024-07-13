# app/services/user_service.py
from fastapi import Depends, status, HTTPException
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
from ..models.payment_schemas import Payment, PaymentType


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
        self, created_lesson: dict, has_paid: bool
    ):
        now = datetime.utcnow()
        payment_data = Payment(
            user_id=created_lesson["user_id"],
            amount=created_lesson["lesson_fee"],
            payment_type=PaymentType.PRIVATE_LESSON,
            paid=has_paid,
            month=now.month,
            year=now.year,
        )
        created_payment = await self.create(payment_data.dict(exclude_unset=True))

        return created_payment

    async def pay_for_private_lesson(self, lesson_id: str):
        result = await self.collection.update_one(
            {"_id": lesson_id},
            {"$set": {"paid": True, "paid_date": datetime.utcnow()}},
        )
        return result.modified_count > 0
