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
from app.models.team_schemas import (
    CreateTeamSchema,
    UserInsert,
    TeamPlayers,
    TeamQueryById,
    TeamCoachesQuery,
)

BASE_URL = "http://localhost:80"  # Adjust if needed


@pytest.fixture
def team_data():
    return {
        "team_name": "Test Team",
        "team_players": [str(ObjectId()), str(ObjectId())],
        "team_coaches": [str(ObjectId())],
        "province": "Test Province",
    }


async def create_test_team(client):
    team_data = {
        "team_name": "Test Team",
        "team_players": [str(ObjectId()), str(ObjectId())],
        "team_coaches": [str(ObjectId())],
        "province": "Test Province",
    }
    response = await client.post("/api/teams/create", json=team_data)
    if response.status == 500:
        print(f"Error creating team: {await response.text()}")
    assert response.status in [201, 200]  # Accept either Created or OK
    data = await response.json()
    return data.get("_id")


@pytest.mark.asyncio
async def test_create_team(api_client, event_loop):
    async def _test(client):
        team_id = await create_test_team(client)

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_insert_users_to_teams(api_client, event_loop):
    async def _test(client):
        team_ids = "66800f9cc5e4ed61fc5fba2f"
        user_ids = ["66957d9049b6287a81bb1bf2"]
        insert_data = {"team_ids": [team_ids], "user_ids": user_ids}
        response = await client.post(
            "/api/teams/insert_users_to_teams", json=insert_data
        )
        assert response.status in [201, 200]  # Accept either Created or OK
        data = await response.json()
        assert "results of player/user insertion" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_team_users(api_client, event_loop):
    async def _test(client):
        team_id = "66800f9cc5e4ed61fc5fba2f"
        payload = {"team_id": team_id}
        response = await client.post("/api/teams/get_team_users", json=payload)
        assert response.status == 200
        data = await response.json()
        assert "player_infos" in data
        assert "coach_infos" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_team_by_id(api_client, event_loop):
    async def _test(client):
        team_id = "66800f9cc5e4ed61fc5fba2f"
        payload = {"team_ids": [team_id]}
        response = await client.post("/api/teams/get_team_by_id", json=payload)
        assert response.status == 200
        data = await response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "_id" in data[0]

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_team_coaches(api_client, event_loop):
    async def _test(client):
        team_id = "66803b315f972429f5dcaa94"
        payload = {"team_ids": [team_id]}
        response = await client.post("/api/teams/get_team_coaches", json=payload)
        assert response.status == 200
        data = await response.json()
        assert isinstance(data, list)

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_all_coaches_by_province(api_client, event_loop):
    async def _test(client):
        province = "Test Province"
        response = await client.get(
            f"/api/teams/get_all_coaches_by_province/{province}"
        )
        if response.status == 500:
            print(f"Error getting coaches: {await response.text()}")
        assert response.status == 200
        data = await response.json()
        assert "coaches" in data
        assert isinstance(data["coaches"], list)
        assert "has_more" in data
        assert "next_cursor" in data

    await run_test(api_client, _test)
