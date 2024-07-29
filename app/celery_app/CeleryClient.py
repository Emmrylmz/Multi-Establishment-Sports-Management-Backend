from celery import Celery
from celery.result import AsyncResult
from functools import wraps


class CeleryClient:
    def __init__(self, app_name: str, broker_url: str, backend_url: str = None):
        self.app = Celery(app_name, broker=broker_url, backend=backend_url)
        self.user_options = {"worker": []}
        self.app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
        )

    @property
    def conf(self):
        return self.app.conf

    def task(self, *args, **kwargs):
        return self.app.task(*args, **kwargs)

    def send_task(self, name, args=None, kwargs=None, **options):
        return self.app.send_task(name, args=args, kwargs=kwargs, **options)

    def get_result(self, task_id):
        return AsyncResult(task_id, app=self.app)

    def revoke_task(self, task_id, terminate=False):
        return self.app.control.revoke(task_id, terminate=terminate)

    def register_task(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return self.app.task(wrapper)

    def __getattr__(self, name):
        return getattr(self.app, name)
