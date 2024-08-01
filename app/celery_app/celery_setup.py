from ..config import settings
from .CeleryClient import CeleryClient
from collections import deque

celery_app = CeleryClient(
    app_name="foo_app",
    broker_url=settings.RABBITMQ_URL,
    backend_url=settings.REDIS_URL,
)


# This will be used to register tasks
def celery_task(func):
    return celery_app.register_task(func)


@celery_app.task(bind=True)
def init_celery_app(self):
    connect_to_mongo_sync()


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        30.0,  # Run every 30 seconds
        init_celery_app.s(),
        name="initialize database connection",
    )


# @celery_app.task(bind=True)
# def close_db_connection(self):
#     close_mongo_connection()


# @celery_app.on_after_finalize.connect
# def shutdown_celery(sender, **kwargs):
#     # close_db_connection.delay()

celery = celery_app.app
