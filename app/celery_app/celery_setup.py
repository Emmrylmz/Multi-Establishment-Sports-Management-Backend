from ..config import settings
from .CeleryClient import CeleryClient
from celery.signals import worker_process_init, worker_process_shutdown
from .celery_db_access import db
from celery.schedules import crontab

celery_app = CeleryClient(
    app_name="foo_app",
    broker_url=settings.RABBITMQ_URL,
    backend_url=settings.REDIS_URL,
)

celery_app.conf.broker_connection_retry_on_startup = True
celery_app.autodiscover_tasks(["app.celery_app"])


@worker_process_init.connect
def init_worker(**kwargs):
    db.connect()


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    db.close()


def celery_task(func):
    def wrapper(*args, **kwargs):
        return func(db, *args, **kwargs)

    return celery_app.register_task(wrapper)


celery = celery_app.app
