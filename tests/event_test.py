import pytest
import aiohttp
import asyncio
from bson import ObjectId
from datetime import datetime, timedelta
from aiohttp import ClientTimeout, ClientSession, TCPConnector

BASE_URL = "http://localhost:80"  # Adjust if needed


class AsyncAPIClient:
    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}
        self.session = None
        self.timeout = ClientTimeout(total=60)

    async def create_session(self):
        if self.session is None or self.session.closed:
            connector = TCPConnector(limit=100, force_close=False)
            self.session = ClientSession(
                headers=self.headers, connector=connector, timeout=self.timeout
            )
        return self.session

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def request(self, method, path, **kwargs):
        url = f"{BASE_URL}{path}"
        session = await self.create_session()
        try:
            async with getattr(session, method)(url, **kwargs) as response:
                await response.read()
                return response
        except asyncio.TimeoutError:
            pytest.fail(f"Request timed out: {method.upper()} {path}")
        except aiohttp.ClientError as e:
            pytest.fail(f"Request failed: {str(e)}")

    async def get(self, path, **kwargs):
        return await self.request("get", path, **kwargs)

    async def post(self, path, **kwargs):
        return await self.request("post", path, **kwargs)

    async def put(self, path, **kwargs):
        return await self.request("put", path, **kwargs)

    async def delete(self, path, **kwargs):
        return await self.request("delete", path, **kwargs)


async def get_access_token():
    login_data = {
        "email": "emir11@example.com",
        "password": "strongpassword",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/api/auth/login",
                json=login_data,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                assert response.status == 200, "Login failed"
                data = await response.json()
                return data["access_token"]
    except aiohttp.ClientError as e:
        pytest.fail(f"Failed to get access token: {str(e)}")


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def api_client(event_loop):
    asyncio.set_event_loop(event_loop)
    access_token = await get_access_token()
    client = AsyncAPIClient(access_token)
    yield client
    await client.close_session()


async def run_test(api_client, test_func, *args, **kwargs):
    try:
        await test_func(api_client, *args, **kwargs)
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")


@pytest.fixture
def event_data():
    return {
        "event_type": "game",
        "place": "Test Stadium",
        "start_datetime": datetime.now().isoformat(),
        "end_datetime": (datetime.now() + timedelta(hours=2)).isoformat(),
        "created_at": datetime.now().isoformat(),
        "team_id": str(ObjectId()),
        "description": "Test Event",
        "creator_id": str(ObjectId()),
    }


@pytest.mark.asyncio
async def test_create_event(api_client, event_loop, event_data):
    async def _test(client):
        response = await client.post("/api/events/create", json=event_data)
        assert response.status == 201
        data = await response.json()
        assert "event_id" in data
        assert data["status"] == "created"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_get_event(api_client, event_loop):
    async def _test(client):
        event_id = "668d44ac1b0d0f472c2c1302"
        response = await client.get(f"/api/events/{event_id}")
        assert response.status == 200
        data = await response.json()
        assert "_id" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_update_event(api_client, event_loop):
    async def _test(client):
        event_id = "668d44ac1b0d0f472c2c1302"
        update_data = {"place": "New Stadium", "description": "Updated description"}
        response = await client.post(f"/api/events/update/{event_id}", json=update_data)
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "changed"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_delete_event(api_client, event_loop):
    async def _test(client):
        event_id = "668d450e1b0d0f472c2c1304"
        response = await client.delete(f"/api/events/delete/{event_id}")
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "deleted"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_fetch_team_events(api_client, event_loop):
    async def _test(client):
        team_ids = ["66840d1185fcf2f44403b1de"]
        response = await client.post(
            "/api/events/get_team_events", json={"team_ids": team_ids}
        )
        assert response.status == 200
        data = await response.json()
        assert isinstance(data, list)

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_add_attendances_to_event(api_client, event_loop):
    async def _test(client):
        attendance_data = {
            "event_id": "668d44ac1b0d0f472c2c1302",
            "attendances": [{"user_id": str(ObjectId()), "status": "present"}],
        }
        response = await client.post(
            "/api/events/add_attendances_to_event", json=attendance_data
        )
        assert response.status == 201
        data = await response.json()
        assert "message" in data

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_create_private_lesson_request(api_client, event_loop):
    async def _test(client):
        lesson_data = {
            "place": "Test Place",
            "start_datetime": datetime.now().isoformat(),
            "end_datetime": (datetime.now() + timedelta(hours=1)).isoformat(),
            "description": "Test Lesson",
            "player_id": str(ObjectId()),
            "lesson_fee": 50.0,
            "paid": False,
            "coach_id": str(ObjectId()),
        }
        response = await client.post(
            "/api/events/create/private_lesson", json=lesson_data
        )
        assert response.status == 201
        data = await response.json()
        assert "request_id" in data
        assert data["status"] == "request_created"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_fetch_attendances_for_event(api_client, event_loop):
    async def _test(client, sample_event_id="668d44ac1b0d0f472c2c1302"):
        # Test with default parameters
        response = await client.post(
            "/api/events/fetch_attendances_for_event",
            json={"event_id": sample_event_id},
        )
        assert response.status == 200
        data = await response.json()

        assert "attendances" in data
        assert "has_next" in data
        assert "next_cursor" in data
        assert len(data["attendances"]) <= 20  # Default limit

        # Verify the structure of returned attendances
        for attendance in data["attendances"]:
            assert "user_id" in attendance
            assert "status" in attendance
            assert "timestamp" in attendance

        # Test with custom parameters
        custom_params = {
            "event_id": sample_event_id,
            "fields": ["user_id", "status"],
            "limit": 2,
        }
        response = await client.post(
            "/api/events/fetch_attendances_for_event", json=custom_params
        )
        assert response.status == 200
        data = await response.json()

        # assert len(data["attendances"]) <= 2
        for attendance in data["attendances"]:
            assert set(attendance.keys()) == {"_id", "timestamp", "user_id", "status"}

        # Test pagination
        if data["has_next"]:
            next_page_params = {
                "event_id": sample_event_id,
                "cursor": data["next_cursor"],
                "limit": 2,
            }
            response = await client.post(
                "/api/events/fetch_attendances_for_event", json=next_page_params
            )
            assert response.status == 200
            next_page_data = await response.json()

            assert len(next_page_data["attendances"]) > 0
            assert (
                next_page_data["attendances"][0]["_id"]
                != data["attendances"][-1]["_id"]
            )

        # Test with non-existent event_id
        non_existent_id = str(ObjectId())
        response = await client.post(
            "/api/events/fetch_attendances_for_event",
            json={"event_id": non_existent_id},
        )
        assert response.status == 200
        data = await response.json()
        assert len(data["attendances"]) == 0
        assert not data["has_next"]
        assert data["next_cursor"] is None

        # Test cache (this is a basic check, as we can't directly verify Redis in this test)
        response1 = await client.post(
            "/api/events/fetch_attendances_for_event",
            json={"event_id": sample_event_id},
        )
        response2 = await client.post(
            "/api/events/fetch_attendances_for_event",
            json={"event_id": sample_event_id},
        )
        assert await response1.json() == await response2.json()

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_update_attendances(api_client, event_loop):
    async def _test(client):
        event_id = "668d44ac1b0d0f472c2c1302"
        attendances = [
            {"user_id": str(ObjectId()), "status": "present"},
        ]

        payload = {"event_id": event_id, "attendances": attendances}

        response = await client.put("/api/events/update_attendances", json=payload)
        assert response.status == 200
        data = await response.json()

        assert data["event_id"] == event_id
        # assert data["status"] == "success"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_approve_private_lesson_request(api_client, event_loop):
    async def _test(client):
        lesson_id = "66ae79c2a5ad310df271adee"

        payload = {
            "place": "Tennis Court 1",
            "start_datetime": "2023-08-10T14:00:00",
            "end_datetime": "2023-08-10T15:00:00",
            "description": "Private tennis lesson",
            "lesson_fee": 50.0,
            "paid": False,
            "response_notes": "Approved lesson",
        }

        response = await client.post(
            f"/api/events/approve/private_lesson_response/{lesson_id}",
            json=payload,
        )
        assert response.status == 200
        data = await response.json()

        assert "lesson_id" in data
        assert data["status"] == "lesson_approved"

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_fetch_coach_private_lessons(api_client, event_loop):
    async def _test(client):
        coach_id = str(ObjectId())

        response = await client.get(f"/api/events/coach_private_lessons/{coach_id}")
        assert response.status == 200
        data = await response.json()

        assert isinstance(data, list)
        # Add more specific assertions based on the expected structure of the response

    await run_test(api_client, _test)


@pytest.mark.asyncio
async def test_fetch_player_private_lessons(api_client, event_loop):
    async def _test(client):
        player_id = str(ObjectId())

        response = await client.get(f"/api/events/player_private_lessons/{player_id}")
        assert response.status == 200
        data = await response.json()

        assert isinstance(data, list)
        # Add more specific assertions based on the expected structure of the response

    await run_test(api_client, _test)


# Add more test functions for other endpoints as needed
