from ..config import settings
from .CeleryClient import CeleryClient
from celery.signals import worker_process_init, worker_process_shutdown
from .celery_db_access import db, get_db_connection
from celery.schedules import crontab
from functools import wraps
from .celery_redis_access import sync_redis_client, get_sync_redis_client
from celery.exceptions import Retry

celery_app = CeleryClient(
    app_name="foo_app",
    broker_url=settings.RABBITMQ_URL,
    backend_url=settings.REDIS_URL,
)

celery_app.conf.broker_connection_retry_on_startup = True
celery_app.autodiscover_tasks(["app.celery_app.celery_tasks"])


@worker_process_init.connect
def init_worker(**kwargs):
    db.connect()
    sync_redis_client.init_redis_pool()


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    db.close()
    sync_redis_client.close()


def with_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with get_db_connection() as database:
            return func(database, *args, **kwargs)

    return wrapper


def with_redis(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with get_sync_redis_client() as redis_conn:
            return func(redis_conn, *args, **kwargs)

    return wrapper


def celery_task(*decorators, max_retries=3, countdown=60):
    def decorator(original_func):
        @wraps(original_func)
        def wrapper(self, *args, **kwargs):
            func = original_func  # Start with the original function
            try:
                # Apply decorators
                for dec in reversed(decorators):
                    func = dec(func)

                # Execute the decorated function
                return func(*args, **kwargs)
            except Exception as exc:
                try:
                    self.retry(exc=exc, max_retries=max_retries, countdown=countdown)
                except Retry as retry:
                    raise retry
                except Exception as retry_exc:
                    raise retry_exc from exc

        return celery_app.register_task(wrapper)

    return decorator


celery = celery_app.app
