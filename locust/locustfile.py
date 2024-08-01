from locust import FastHttpUser, task, between
from datetime import datetime, timedelta
import random

JWT = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI2Njc4ODUzOTllMjAzODZjMzhkN2QwM2UiLCJpYXQiOjE3MjI0NDQ1MTMsIm5iZiI6MTcyMjQ0NDUxMywianRpIjoiNTU0MmQ3ZmQtM2Q3Ni00ZDQ1LTg0YjItOTIzYzgzYmNjY2JjIiwiZXhwIjoxNzIyNDY4NTEzLCJ0eXBlIjoiYWNjZXNzIiwiZnJlc2giOmZhbHNlfQ.UzldA1ZU9rG0k9rNQmy7AEaUaObFz-yc6kYewRbf2Be6ImQotgkyI4ixLwxMEgY-mn_Dtx6x9qP2-wuaBKbUUO_aJlNohBrJ09sxaHvQJae3EEaBersyxPiCCX_cH_xRl737srAsaonmkcQNJYNvjQQk0nsFSiBO8JCqcym3Ng8ITl5uguE1H8Et7dE41fLqPYmLuh5ejxsMd5pbSdtx-CEwH_kDYbOWhI_RUwHW5yJc41A21_o42RdOnW2Yz5EPwXRQ7XIW-uLF-_UFLeJxIfkXWLnPKO_pMAInKPB42D3GOKJKXfJMbMgJVnZ1paos7R_02JsQ-bfNCf3xNvHXkQ"


class FastAPIUser(FastHttpUser):
    wait_time = between(0.1, 1)  # Reduced wait time
    api_prefix = "/api"

    def on_start(self):
        self.headers = {"Authorization": f"Bearer {JWT}"}
        self.client.keep_alive = True  # Enable connection pooling

    @task(3)
    def get_event(self):
        event_id = "668d44ac1b0d0f472c2c1302"
        self.client.get(f"{self.api_prefix}/events/{event_id}", headers=self.headers)

    @task(5)
    def fetch_team_events(self):
        payload = {"team_ids": ["66800f9cc5e4ed61fc5fba2f", "66800f9cc5e4ed61fc5fba2f"]}
        self.client.post(
            f"{self.api_prefix}/events/get_team_events",
            json=payload,
            headers=self.headers,
        )

    @task(4)
    def fetch_attendances_for_event(self):
        payload = {"event_id": "668d44ac1b0d0f472c2c1302"}
        self.client.post(
            f"{self.api_prefix}/events/fetch_attendances_for_event",
            json=payload,
            headers=self.headers,
        )

    @task(5)
    def get_team_coaches(self):
        payload = {"team_ids": ["66803b315f972429f5dcaa94", "6683da1449760fc82bdcb1f4"]}
        self.client.post(
            f"{self.api_prefix}/events/get_upcoming_events",
            json=payload,
            headers=self.headers,
        )

    @task(4)
    def get_expected_revenue(self):
        province = "Izmir"
        self.client.get(
            f"{self.api_prefix}/payments/expected_revenue?province={province}",
            headers=self.headers,
        )

    @task(4)
    def get_total_earned(self):
        year = 2024
        province = "Izmir"
        self.client.get(
            f"{self.api_prefix}/payments/get_total_earned/{province}/{year}",
            headers=self.headers,
        )

    @task(1)
    def create_private_lesson_request(self):
        payload = {
            "place": "Test Location",
            "start_datetime": (datetime.now() + timedelta(days=7)).isoformat(),
            "end_datetime": (datetime.now() + timedelta(days=7, hours=1)).isoformat(),
            "description": "Test private lesson",
            "player_id": "667882fd1b21c9bce6f072e6",
            "lesson_fee": round(random.uniform(50, 200), 2),
            "coach_id": "667882fd1b21c9bce6f072e7",
        }
        self.client.post(
            f"{self.api_prefix}/events/create/private_lesson",
            json=payload,
            headers=self.headers,
        )
