from locust import FastHttpUser, task, between
from datetime import datetime, timedelta
import random

JWT = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI2Njc4ODUzOTllMjAzODZjMzhkN2QwM2UiLCJpYXQiOjE3MjI2MDQzNTIsIm5iZiI6MTcyMjYwNDM1MiwianRpIjoiOWM2MzNjNGYtNWRjNi00YWRhLWE5NGItOGY2NDg5MGEzNGYzIiwiZXhwIjoxNzIyNjI4MzUyLCJ0eXBlIjoiYWNjZXNzIiwiZnJlc2giOmZhbHNlfQ.j0IvNCwy1rV1o2hJuKSUrRl8H3mKi75H5-0t-acNnjtZyYYIPkOraCCnjwMaYV_6dATyCeq26_geXrfA9GLVMGA_fZatw8z_j4RQENwGTR-7dc1r-igQ4jxTddhqFTNDsbeurQxWDxa5XFuKXWXXMnNAgF1SH66x0zW1tRoxs6ulh-gy6CVvlSEWgcVm7LyMGwtuhvETueWlIKyKvzI7bSrPRpHGcOCQZmAhL_ZipOU2Qw5oWFF8oFqJxI5t7pJJS9sdVSjOcgac7Am5e_hMknoOIvnRo6dBHN18XXoYxPk5gGj31HoK0AfCtiwnzIqjPwrFWNrvwIDQE5_IMSwXPA"


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
