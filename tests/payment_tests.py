import pytest
import asyncio
from bson import ObjectId
from datetime import datetime, timedelta
from .event_test import (
    AsyncAPIClient,
    run_test,
    get_access_token,
    api_client,
    event_loop,
)
from app.models.payment_schemas import PaymentType, PaymentWith, Status

BASE_URL = "http://localhosst:80"  # Adjust if needed


@pytest.fixture
def payment_data():
    return {
        "user_id": "667882fd1b21c9bce6f072e6",
        "payment_type": PaymentType.MONTHLY,
        "payment_with": PaymentWith.CREDIT_CARD,
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "amount": 100.0,
        "paid_amount": 0,
        "remaining_amount": 100.0,
        "status": Status.PENDING,
        "month": datetime.now().month,
        "year": datetime.now().year,
        "province": "Izmir",
        "description": "Test Payment",
    }


@pytest.fixture
def payment_data_for_update():
    return {
        "_id": "66a4d8a89b3e5897035e26e2",
        "user_id": "667882fd1b21c9bce6f072e6",
        "payment_type": PaymentType.MONTHLY,
        "payment_with": PaymentWith.CREDIT_CARD,
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "amount": 100.0,
        "paid_amount": 0,
        "remaining_amount": 100.0,
        "status": Status.PENDING,
        "month": datetime.now().month,
        "year": datetime.now().year,
        "province": "Izmir",
        "description": "Test Payment",
    }


@pytest.mark.asyncio
async def test_create_payment_for_months(api_client, event_loop, payment_data):
    async def _test(client):
        create_data = {
            "user_id": payment_data["user_id"],
            "months_and_amounts": {str(payment_data["month"]): 50.0},
            "default_amount": payment_data["amount"],
            "payment_with": payment_data["payment_with"],
            "year": payment_data["year"],
            "province": payment_data["province"],
        }
        response = await client.post(
            "/api/payments/create_payment_for_months", json=create_data
        )
        assert response.status == 201
        data = await response.json()
        assert "status" in data
        assert data["status"] == "success"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_update_payment_for_months(
    api_client, event_loop, payment_data_for_update
):
    async def _test(client):
        update_data = {
            "year": payment_data_for_update["year"],
            "province": payment_data_for_update["province"],
            "user_id": payment_data_for_update["user_id"],
            "default_amount": payment_data_for_update["amount"],
            "payments": [
                {
                    "_id": payment_data_for_update["_id"],
                    "month": payment_data_for_update["month"],
                    "paid_amount": 75.0,
                    "payment_with": PaymentWith.CASH,
                }
            ],
        }
        response = await client.post(
            "/api/payments/update_payment_for_months", json=update_data
        )
        assert response.status == 201
        data = await response.json()
        assert "status" in data
        assert data["status"] == "success"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_update_payment(api_client, event_loop, payment_data_for_update):
    async def _test(client):
        payment_id = payment_data_for_update["_id"]
        update_data = {
            "paid_amount": 100.0,
            "amount": 200.0,
        }
        response = await client.put(
            f"/api/payments/update/{payment_id}", json=update_data
        )
        assert response.status == 200
        data = await response.json()
        assert "_id" in data["payment"]

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_delete_payment(api_client, event_loop):
    async def _test(client):
        payment_id = "66a8342a29cc33d805504234"
        response = await client.delete(f"/api/payments/delete/{payment_id}")
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "success"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_user_data_by_year(api_client, event_loop, payment_data):
    async def _test(client):
        user_id = payment_data["user_id"]
        year = payment_data["year"]
        response = await client.get(f"/api/payments/{user_id}/{year}")
        assert response.status == 200
        data = await response.json()
        assert isinstance(data, list)

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_make_single_payment(api_client, event_loop, payment_data):
    async def _test(client):
        response = await client.post(
            "/api/payments/make_single_payment", json=payment_data
        )
        assert response.status == 200
        data = await response.json()

    await run_test(api_client, _test)


# @pytest.mark.asyncio
# async def test_get_team_payments(api_client, event_loop):
#     async def _test(client):
#         team_id = str(ObjectId())
#         response = await client.get(f"/api/payments/get_team_payments/{team_id}")
#         assert response.status == 200
#         data = await response.json()
#         assert isinstance(data, list)

#     await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_expected_revenue(api_client, event_loop):
    async def _test(client):
        province = "Izmir"
        response = await client.get(
            f"/api/payments/expected_revenue?province={province}"
        )
        assert response.status == 200
        data = await response.json()
        assert "expected_yearly_revenue" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_total_earned(api_client, event_loop):
    async def _test(client):
        year = datetime.now().year
        province = "Izmir"
        response = await client.get(f"/api/payments/get_total_earned/{province}/{year}")
        assert response.status == 200
        data = await response.json()
        assert "total_earned_overall" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_enter_expenses(api_client, event_loop):
    async def _test(client):
        expense_data = {
            "user_id": str(ObjectId()),
            "payment_with": PaymentWith.BANK_TRANSFER,
            "amount": -500.0,
            "description": "Test Expense",
            "month": datetime.now().month,
            "year": datetime.now().year,
            "province": "Izmir",
        }
        response = await client.post("/api/payments/expenses/enter", json=expense_data)
        assert response.status == 201
        data = await response.json()
        assert data["status"] == Status.PAID
        assert data["amount"] == -500.0

    await run_test(api_client, _test)
