"""
RabbitClient Package

This package provides a client for interacting with RabbitMQ,
specifically tailored for handling various types of notifications.
"""

from .client import RabbitClient

__all__ = ["RabbitClient"]

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "A RabbitMQ client for handling notifications"


# You could also include convenience functions
def create_client(rabbit_url, push_token_service):
    """
    Convenience function to create and return a RabbitClient instance.
    """
    return RabbitClient(rabbit_url, push_token_service)


# Or constants
DEFAULT_EXCHANGE = "notifications_exchange12"

# If you want to expose these as well, add them to __all__
__all__ += ["create_client", "DEFAULT_EXCHANGE"]
