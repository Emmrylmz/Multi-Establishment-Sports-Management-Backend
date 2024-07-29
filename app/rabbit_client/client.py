from .connection import ConnectionMixin
from ..service.TokenService import PushTokenService
from .message_processing import MessageProcessingMixin
from .queue_management import QueueManagementMixin
from .message_publishing import MessagePublishingMixin
from .push_notifications import PushNotificationsMixin
from .team_notifications import TeamNotificationsMixin
from typing import Optional
from ..utils import setup_logger

logger = setup_logger(__name__)


class RabbitClient(
    ConnectionMixin,
    MessageProcessingMixin,
    QueueManagementMixin,
    MessagePublishingMixin,
    PushNotificationsMixin,
    TeamNotificationsMixin,
):
    def __init__(
        self,
        rabbit_url: str,
        push_token_service: PushTokenService,
        service: Optional[str] = None,
        exchange_name: str = "notifications_exchange12",
    ):
        super().__init__()  # This will initialize all the mixins
        self.rabbit_url = rabbit_url
        self.push_token_service = push_token_service
        self.service_name = service
        self.exchange_name = exchange_name
        self.channel = None
        self.connection = None
        self.exchange = None
        self.message_handler = (
            self._process_incoming_message
        )  # From MessageProcessingMixin

        logger.info("RabbitClient initialized")

    async def start(self):
        await super().start()  # This will call the start method from ConnectionMixin
        logger.info("RabbitClient started")

    async def stop(self):
        await super().stop()  # This will call the stop method from ConnectionMixin
        logger.info("RabbitClient stopped")
