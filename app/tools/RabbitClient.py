import asyncio
from typing import Callable, Optional, Any
import json
from aio_pika.exceptions import AMQPConnectionError
from aio_pika import (
    DeliveryMode,
    connect_robust,
    RobustConnection,
    IncomingMessage,
    Message,
)
from ..config import settings
from bson import json_util
import logging
from ..tools.ExponentServerSDK import push_client, PushMessage
import aio_pika
from datetime import datetime
from ..utils import DateTimeEncoder
from ..service.TokenService import push_token_service


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class RabbitClient:
    """This class implements RabbitMQ Publish and Subscribe async handling.

    The RabbitMQ queue mechanism is used so that we can take advantage of
    good horizontal message scaling when needed.

    :ivar channel: RabbitMQ's connection channel object instance.
    :type channel: aio_pika.AbstractChannel
    :ivar rabbit_url: RabbitMQ's connection URL.
    :ivar service_name: Name of message subscription queue.
    :ivar message_handler: Received message callback method.
    :ivar connection: RabbitMQ's connection object instance.
    :type connection: aio_pika.AbstractRobustConnection
    """

    # ---------------------------------------------------------
    #
    def __init__(
        self,
        rabbit_url: str,
        service: Optional[str] = None,
        exchange_name: str = "notifications_exchange12",
    ):
        """The class initializer.

        :param rabbit_url: RabbitMQ's connection URL.
        :param service: Name of message subscription queue.
        :param incoming_message_handler: Received message callback method.
        """
        self.channel = None
        self.connection = None
        self.rabbit_url = rabbit_url
        self.service_name = service
        self.message_handler = self._process_incoming_message
        self.exchange = None
        self.exchange_name = exchange_name

    # ---------------------------------------------------------
    #
    def _process_incoming_message(self, message: IncomingMessage):
        """Processing an incoming message from RabbitMQ.

        :param message: The received message.
        """
        logging.debug("Starting message processing")
        try:
            message_body = message.body.decode()  # Decode bytes to string
            data = json.loads(message_body)  # Parse JSON string to dictionary

            logging.debug(f"Received the message: {data}")
            self.handle_push_notification(data)
        except json.JSONDecodeError as e:
            logging.error(
                f"JSON decode error: {e} - Message Body: {message.body.decode()}"
            )
        except Exception as e:
            logging.error(f"Failed to process message: {str(e)}")

    def handle_push_notification(self, data):
        # Here you'd use the details from `data` to create your push message
        logging.debug(f"Received data for push notification: {data}")
        push_token_service.get_team_player_tokens(data["team_id"])
        push_message = PushMessage(
            to="ExponentPushToken[6Nn4MnPCDEj77x1HHAiKdg]",
            title="New Message From Your Coach !!",
            body="Check it out that",
            data={"message": data},
        )
        try:
            # Send the notification
            ticket = push_client.publish(push_message)
            return {"status": "Success", "ticket": ticket}

        except Exception as e:
            # Catch any broad exceptions and return as HTTP error
            logging.error(f"Failed to process message: {str(e)}")

    # ---------------------------------------------------------
    #
    def _on_connection_closed(self, _: Any, __: AMQPConnectionError):
        """Handle unexpectedly closed connection events.

        :param _: Not used.
        :param __: Not used.
        """
        self.connection = None

    # ---------------------------------------------------------
    #
    async def _on_connection_reconnected(self, connection: RobustConnection):
        """Send a LinkUp message when the connection is reconnected.

        :param connection: RabbitMQ's robust connection instance.
        """
        self.connection = connection

    # ---------------------------------------------------------
    #
    async def _initiate_communication(self):
        """Establish communication with RabbitMQ (connection + channel).
        Send a LinkUp message when communication is established.
        """
        loop = asyncio.get_running_loop()

        # Create a RabbitMQ connection that automatically reconnects.
        self.connection = await connect_robust(loop=loop, url=self.rabbit_url)

        # Set reconnection and closure callbacks.
        self.connection.reconnect_callbacks.add(self._on_connection_reconnected)
        self.connection.close_callbacks.add(self._on_connection_closed)

        # Establish a channel.
        self.channel = await self.connection.channel()

        # Declare the exchange using the newly established channel.
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
        )

        # Set Quality of Service for the channel.
        await self.channel.set_qos(prefetch_count=1)

    # ---------------------------------------------------------

    # ---------------------------------------------------------
    #

    # async def publish_message(self, queue: str, message: dict):
    #     """Publish a message on specified RabbitMQ queue asynchronously.

    #     :param queue: Publishing queue.
    #     :param message: Message to be published.
    #     """

    #     try:
    #         message_body = Message(
    #             content_type="application/json",
    #             delivery_mode=DeliveryMode.PERSISTENT,
    #             body=json.dumps(
    #                 message, indent=4, sort_keys=True, default=str
    #             ).encode(),
    #         )
    #         await self.channel.default_exchange.publish(
    #             routing_key=queue, message=message_body
    #         )
    #         logging.info(f"Message published to {queue}")
    #     except Exception as e:
    #         logging.error(f"Failed to publish message to {queue}: {e}")
    #         raise

    async def declare_and_bind_queue(self, queue_name: str, routing_keys: list):
        """Declare a new queue and bind it with specific routing keys."""
        queue = await self.channel.declare_queue(queue_name, durable=True)
        for routing_key in routing_keys:
            await queue.bind(self.exchange, routing_key=routing_key)
        logging.info(
            f"Queue {queue_name} declared and bound with routing keys: {routing_keys}"
        )

    async def publish_message(self, routing_key: str, message: dict):
        """Publish a message with specific routing keys."""
        # if hasattr(message, "dict"):
        #     message = message.dict()

        body = json.dumps(message, indent=4, sort_keys=True, default=str).encode()
        msg = Message(
            body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        await self.exchange.publish(msg, routing_key=routing_key)
        logging.info(f"Message published to {routing_key}")

    async def start_consumer(self, queue_name: str):
        """Start consuming messages from a specified queue."""
        queue = await self.channel.get_queue(queue_name)
        await queue.consume(self._process_incoming_message)
        logging.info(f"Started consuming from {queue_name}")

    # ---------------------------------------------------------
    #
    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return False if self.connection is None else not self.connection.is_closed

    # ---------------------------------------------------------
    #
    async def start(self):
        """Start the used resources in a controlled way."""
        await self._initiate_communication()

    # ---------------------------------------------------------
    #
    async def stop(self):
        """Stop the used resources in a controlled way."""
        if self.connection:
            await self.connection.close()
