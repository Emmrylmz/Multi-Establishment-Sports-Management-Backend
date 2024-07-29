from .celery_setup import celery_app

if __name__ == "__main__":
    celery_app.app.start()
    print("celery", celery_app.app.control.ping())
