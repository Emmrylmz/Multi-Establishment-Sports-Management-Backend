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


@pytest.mark.asyncio
async def test_update_user_information(api_client):
    async def _test(client):
        user_data = {
            "name": "Updated User",
            "age": 30,
            "height": 180.5,
            "weight": 75.0,
            "photo": "https://example.com/photo.jpg",
            "contact_info": [{"phone": "1234567890"}],
            "family_contacts": [
                {
                    "name": "Family Member",
                    "email": "family@example.com",
                    "phone": "9876543210",
                }
            ],
            "on_boarding": False,  # Change this to False to trigger an update instead of create
            "created_at": datetime.now().isoformat(),
            "discount": 10.5,
            "discount_reason": "Loyalty discount",
        }
        response = await client.post("/api/user_info/update", json=user_data)
        assert response.status == 200
        data = await response.json()
        # assert "status" in data
        # assert data["status"] == "success"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_user_information(api_client):
    async def _test(client):
        # You need to use a valid user ID here. Consider creating a user first in a setup function.
        user_id = "66957e32fd1325deae5d7c89"  # Replace with a valid user ID
        response = await client.get(f"/api/user_info/{user_id}")
        assert response.status == 200
        data = await response.json()
        assert "_id" in data
        assert data["_id"] == user_id

    await run_test(api_client, _test)


# @pytest.mark.asyncio
# async def test_search_users_by_name(api_client):
#     async def _test(client):
#         query = "John"
#         response = await client.get("/api/user_info/search", json={"query": query})
#         assert response.status == 200
#         data = await response.json()
#         assert isinstance(data, list)
#         if len(data) > 0:
#             assert "name" in data[0]
#             assert query.lower() in data[0]["name"].lower()

#     await run_test(api_client, _test)


# @pytest.mark.asyncio
# async def test_get_users_by_province(api_client):
#     async def _test(client):
#         province = "Izmir"
#         response = await client.get(
#             "/api/user_info/search", json={"province": province}
#         )
#         assert response.status == 200
#         data = await response.json()
#         assert isinstance(data, list)
#         if len(data) > 0:
#             assert "province" in data[0]
#             assert data[0]["province"] == province

#     await run_test(api_client, _test)
