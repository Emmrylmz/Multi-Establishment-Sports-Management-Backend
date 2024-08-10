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
from app.models.user_schemas import UserRole, CreateUserSchema, LoginUserSchema
from app.models.firebase_token_schemas import PushTokenSchema

BASE_URL = "http://10.22.99.210:80"  # Adjust if needed


@pytest.mark.asyncio
async def test_register(api_client, event_loop):
    async def _test(client):
        register_data = {
            "email": f"test_user_{ObjectId()}@example.com",
            "password": "strongpassword",
            "passwordConfirm": "strongpassword",
            "name": "Test User",
            "role": "Player",
            "teams": ["66800f9cc5e4ed61fc5fba2f"],
            "province": "Test Province",
        }
        response = await client.post("/api/auth/register", json=register_data)
        assert response.status == 201
        data = await response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "user" in data
        assert "_id" in data["user"]

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_login(api_client, event_loop):
    async def _test(client):
        login_data = {
            "email": "emir11@example.com",
            "password": "strongpassword",
        }
        response = await client.post("/api/auth/login", json=login_data)
        assert response.status == 200
        data = await response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_refresh_token(api_client, event_loop):
    async def _test(client):
        # First, login to get a refresh token
        login_data = {
            "email": "emir11@example.com",
            "password": "strongpassword",
        }
        login_response = await client.post("/api/auth/login", json=login_data)
        login_data = await login_response.json()
        refresh_token = login_data["refresh_token"]

        # Now, use the refresh token to get a new access token
        client.headers["Authorization"] = f"Bearer {refresh_token}"
        response = await client.get("/api/auth/refresh_token")
        assert response.status == 200
        data = await response.json()
        assert "access_token" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_logout(api_client, event_loop):
    async def _test(client):
        response = await client.get("/api/auth/logout")
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "success"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_push_token(api_client, event_loop):
    async def _test(client):
        push_token_data = {
            "token": "example_push_token",
            "device_id": "example_device_id",
        }
        response = await client.post("/api/auth/push_token", json=push_token_data)
        assert response.status == 201
        data = await response.json()
        assert "result" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_delete_user(api_client, event_loop):
    async def _test(client):
        # First, register a new user
        register_data = {
            "email": f"delete_user_{ObjectId()}@example.com",
            "password": "strongpassword",
            "passwordConfirm": "strongpassword",
            "name": "Delete User",
            "role": "Player",
            "teams": ["66800f9cc5e4ed61fc5fba2f"],
            "province": "Test Province",
        }
        register_response = await client.post("/api/auth/register", json=register_data)
        register_data = await register_response.json()
        user_id = register_data["user"]["_id"]

        # Now, delete the user
        response = await client.get(f"/api/auth/delete_user/{user_id}")
        assert response.status == 200
        data = await response.json()
        assert "deleted_user" in data
        assert "deleted_team" in data
        assert data["deleted_user"]["deleted_count"] == 1

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_check_token(api_client, event_loop):
    async def _test(client):
        response = await client.post("/api/auth/checkToken")
        assert response.status == 200
        data = await response.json()
        assert "message" in data
        assert data["message"] == "You have access to this protected resource"

    await run_test(api_client, _test)
