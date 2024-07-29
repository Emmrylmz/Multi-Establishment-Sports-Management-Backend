# app/services/user_service.py
from fastapi import Depends, status, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from .. import utils
from datetime import datetime, date, timedelta
from bson import ObjectId
import logging
from ..config import settings
from ..database import get_collection
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError
from motor.motor_asyncio import AsyncIOMotorCollection
from ..service.MongoDBService import MongoDBService
from ..models.payment_schemas import (
    Payment,
    PaymentType,
    Status,
    CreatePaymentForMonthsSchema,
    PaymentWith,
    PaymentUpdateList,
    PaymentUpdateResponse,
)
from dateutil.relativedelta import relativedelta
from pymongo import UpdateOne, InsertOne
from enum import Enum
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class PaymentService(MongoDBService):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.balance_collection = get_collection("Monthly_Balances")

    async def update_monthly_balance(
        self, year: int, month: int, province: str, amount_change: float
    ):
        await self.balance_collection.update_one(
            {
                "year": year,
                "month": month,
                "province": province,
                "document_type": "monthly_balance",
            },
            {
                "$inc": {"total_balance": amount_change},
                "$set": {"last_updated": datetime.utcnow()},
            },
            upsert=True,
        )

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
            logger.info(f"MongoDB client: {client}")

            async with await client.start_session() as session:
                async with session.start_transaction():
                    logger.info("Transaction started")

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

                        # Prepare balance update for each month
                        if (year, month) not in balance_updates:
                            balance_updates[(year, month)] = 0
                        balance_updates[(year, month)] += paid_amount

                    if create_operations:
                        logger.info(
                            f"Executing bulk write for {len(create_operations)} payments"
                        )
                        result = await self.collection.bulk_write(
                            create_operations, session=session
                        )
                        logger.info(
                            f"Bulk write completed: {result.inserted_count} documents inserted"
                        )

                        # Update the monthly balance for each month
                        for (year, month), amount in balance_updates.items():
                            await self.update_monthly_balance(
                                year, month, province, amount, session
                            )
                            logger.info(
                                f"Monthly balance updated for year {year}, month {month}, province {province}"
                            )
                    else:
                        logger.info("No payments to create")

                    # Handle next month's ticket
                    await self._handle_next_month_ticket(
                        user_id,
                        year,
                        max(sorted_months),
                        default_amount,
                        province,
                        payment_with,
                        session,
                    )
                    logger.info("Next month's ticket handled")

                logger.info("Transaction and session completed successfully")

            return {
                "status": "success",
                "message": f"Created payments for {len(sorted_months)} months and handled next month's ticket",
                "created_count": result.inserted_count if result else 0,
            }

        except ValueError as ve:
            logger.error(f"ValueError: {str(ve)}")
            raise HTTPException(status_code=400, detail=str(ve))
        except BulkWriteError as bwe:
            logger.error(f"BulkWriteError: {bwe.details}")
            raise HTTPException(status_code=400, detail="Error processing payments")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def update_monthly_payments(self, payment_updates: PaymentUpdateList):
        try:
            client = self.collection.database.client
            async with await client.start_session() as session:
                async with session.start_transaction():
                    update_operations = []
                    balance_updates = {}  # To store balance updates for each month

                    for update in payment_updates.payments:
                        # Fetch the existing payment to calculate amount change
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

                        # Prepare update data
                        update_data = {
                            "paid_amount": new_paid_amount,
                            "remaining_amount": existing_payment["amount"]
                            - new_paid_amount,
                            "status": self._determine_status(
                                new_paid_amount, existing_payment["amount"]
                            ),
                            "updated_at": datetime.utcnow(),
                        }

                        # Add payment method if provided
                        if update.payment_with:
                            update_data["payment_with"] = update.payment_with.value

                        update_operations.append(
                            UpdateOne(
                                {"_id": ObjectId(update.id)}, {"$set": update_data}
                            )
                        )

                        # Prepare balance update
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

                        # Update the monthly balances
                        for (
                            year,
                            month,
                            province,
                        ), amount_change in balance_updates.items():
                            await self.update_monthly_balance(
                                year, month, province, amount_change, session
                            )

                    return PaymentUpdateResponse(
                        status="success",
                        message=f"Updated {len(update_operations)} payments",
                        modified_count=result.modified_count if result else 0,
                    )

        except ValueError as ve:
            logger.error(f"ValueError in update_monthly_payments: {str(ve)}")
            raise HTTPException(status_code=400, detail=str(ve))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in update_monthly_payments: {str(e)}", exc_info=True
            )
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

    async def _get_existing_payments(
        self, user_id: str, year: int, months: List[int], session
    ):
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "year": year,
                    "month": {"$in": months},
                    "payment_type": PaymentType.MONTHLY,
                }
            },
            {"$group": {"_id": "$month", "payment": {"$first": "$$ROOT"}}},
        ]
        result = await self.collection.aggregate(pipeline, session=session).to_list(
            None
        )
        return {doc["_id"]: doc["payment"] for doc in result}

    async def _handle_next_month_ticket(
        self, user_id, year, last_month, default_amount, province, payment_with, session
    ):
        next_month = (last_month + 1) % 12
        next_year = year + 1 if next_month == 0 else year
        next_due_date = datetime(
            next_year, next_month + 1, 1
        )  # Add 1 to get the correct month number

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

    async def update_monthly_balance(self, year, month, province, amount, session):
        await self.balance_collection.update_one(
            {
                "year": year,
                "month": month,
                "province": province,
                "document_type": "monthly_balance",
            },
            {
                "$inc": {"total_balance": amount},
                "$set": {"last_updated": datetime.utcnow()},
            },
            upsert=True,
            session=session,
        )

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

    async def update_payment(self, payment_id: str, update_data: dict):
        # Ensure the payment exists
        old_payment = await self.collection.find_one({"_id": ObjectId(payment_id)})
        if not old_payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # Prepare update data
        update_fields = {}
        allowed_fields = ["amount", "due_date", "status", "province", "paid_amount"]
        for field in allowed_fields:
            if field in update_data:
                update_fields[field] = update_data[field]

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Calculate the amount change for monthly balance update
        old_paid_amount = old_payment.get("paid_amount", 0)
        new_paid_amount = update_fields.get("paid_amount", old_paid_amount)

        # Adjust paid amount based on status change
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

        # Update the paid_amount in update_fields
        update_fields["paid_amount"] = new_paid_amount

        # Perform the update
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(payment_id)},
            {"$set": update_fields},
            return_document=True,
        )

        if not result:
            raise HTTPException(status_code=400, detail="Update failed")

        # Update the monthly balance if the paid amount changed
        if amount_change != 0:
            await self.update_monthly_balance(
                result["year"], result["month"], result["province"], amount_change
            )

        # Handle the next month's ticket if status changed to or from 'paid'
        if "status" in update_fields:
            await self._handle_payment_status_change(old_payment, result)

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

            existing_payment = await self.collection.find_one(
                {"_id": ObjectId(payment_id)}
            )
            if not existing_payment:
                raise ValueError(f"No payment found with id {payment_id}")

            # Calculate the amount change for monthly balance update
            amount_change = payment_dict.get("paid_amount", 0) - existing_payment.get(
                "paid_amount", 0
            )

            result = await self.collection.update_one(
                {"_id": ObjectId(payment_id)}, {"$set": payment_dict}
            )

            if result.modified_count == 0:
                raise ValueError(f"Failed to update payment with id {payment_id}")

            # Update the monthly balance
            await self.update_monthly_balance(
                payment.year, payment.month, payment.province, amount_change
            )

            updated_payment = await self.collection.find_one(
                {"_id": ObjectId(payment_id)}
            )
            return Payment(**updated_payment)
        else:
            # Create new payment
            payment_dict["created_at"] = datetime.utcnow()
            payment_dict["updated_at"] = payment_dict["created_at"]

            result = await self.collection.insert_one(payment_dict)

            # Update the monthly balance
            await self.update_monthly_balance(
                payment.year, payment.month, payment.province, payment.paid_amount
            )

            created_payment = await self.collection.find_one(
                {"_id": result.inserted_id}
            )
        return Payment(**created_payment)

    async def get_expected_yearly_revenue(self, province: str, max_lookback_months=6):
        try:
            current_date = datetime.utcnow()
            current_year = current_date.year
            current_month = current_date.month

            # Calculate the start date for our lookback period
            lookback_start_date = current_date - relativedelta(
                months=max_lookback_months
            )

            # Aggregation pipeline to get the monthly balances for the lookback period
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

            # Calculate average monthly balance for passed months
            total_balance = sum(monthly_balances)
            average_monthly_balance = total_balance / months_count

            # Calculate expected yearly revenue
            remaining_months = 12 - current_month + 1  # Including current month
            expected_yearly_revenue = total_balance + (
                average_monthly_balance * remaining_months
            )

            return {
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

        except Exception as e:
            logger.error(f"Error in get_expected_yearly_revenue: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {str(e)}"
            )

    async def get_total_earned_by_year_and_province(
        self, year: int, province: str = None
    ):
        try:
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

            return JSONResponse(content=response_content)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    async def enter_expenses(self, expense_payment: Payment):
        logger.info(f"Entering expense in service: {expense_payment}")
        try:
            client = self.collection.database.client
            async with await client.start_session() as session:
                async with session.start_transaction():
                    logger.debug("Transaction started")
                    # Create the expense
                    created_expense = await self.create(
                        expense_payment.dict(exclude_unset=True)
                    )
                    logger.debug(f"Expense created: {created_expense}")

                    # Update monthly balance
                    await self.update_monthly_balance(
                        expense_payment.year,
                        expense_payment.month,
                        expense_payment.province,
                        -abs(expense_payment.amount),
                        session,
                    )
                    logger.debug("Monthly balance updated")

            logger.info(f"Expense entered successfully: {created_expense}")
            return Payment(**created_expense)
        except ValidationError as ve:
            logger.error(f"Validation error in enter_expenses: {ve}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except Exception as e:
            logger.exception(f"Unexpected error in enter_expenses: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while entering the expense: {str(e)}",
            )
