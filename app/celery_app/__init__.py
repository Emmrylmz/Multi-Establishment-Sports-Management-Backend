# __init__.py

# Import the CeleryClient class
from .CeleryClient import CeleryClient

# Import the celery app instance and any other necessary items from celery_setup
from .celery_setup import celery_app, celery

# Import all tasks from celery_tasks
from .celery_tasks import *

# If you have specific functions or classes in celery_worker that you want to expose, import them here
# For example:
# from .celery_worker import some_function, SomeClass

# You can also import everything from celery_worker if needed
# from .celery_worker import *

# If you want to define what gets imported when someone does `from your_package import *`,
# you can define __all__
__all__ = [
    "CeleryClient",
    "celery_app",
    "celery",
]  # Add any other items you want to expose

# You can also add any initialization code here if needed
# For example, setting up logging, initializing the Celery app, etc.

# Example:
# import logging
# logging.basicConfig(level=logging.INFO)

# Initialize Celery app if it's not already done in celery_setup
# celery_app.init_app()
