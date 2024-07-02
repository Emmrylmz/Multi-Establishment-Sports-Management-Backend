import asyncio
from typing import Optional, Any
import json
import logging
from aio_pika import (
    DeliveryMode,
    connect_robust,
    RobustConnection,
    IncomingMessage,
    Message,
    ExchangeType,
)
from aio_pika.exceptions import AMQPConnectionError
from fastapi.encoders import jsonable_encoder
from ..tools.ExponentServerSDK import push_client, PushMessage
from ..service.TokenService import PushTokenService

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class RabbitClient:
    """This class implements RabbitMQ Publish and Subscribe async handling."""

    def __init__(
        self,
        rabbit_url: str,
        push_token_service: PushTokenService,
        service: Optional[str] = None,
        exchange_name: str = "notifications_exchange12",
    ):
        self.channel = None
        self.connection = None
        self.rabbit_url = rabbit_url
        self.push_token_service = push_token_service
        self.service_name = service
        self.message_handler = self._process_incoming_message
        self.exchange = None
        self.exchange_name = exchange_name

    async def _process_incoming_message(self, message: IncomingMessage):
        """Processing an incoming message from RabbitMQ."""
        logging.debug("Starting message processing")
        try:
            message_body = message.body.decode()  # Decode bytes to string
            data = json.loads(message_body)
            team_id = data["event"].get("team_id")
            event = data["event"]
            await self.handle_push_notification(event, team_id)

            logging.debug(f"Received the message: {data}")
            await message.ack()

        except json.JSONDecodeError as e:
            logging.error(
                f"JSON decode error: {e} - Message Body: {message.body.decode()}"
            )
        except Exception as e:
            logging.error(f"Failed to process message: {str(e)}")

    async def handle_push_notification(self, data, team_id):
        """Handle the push notification."""
        logging.debug(f"Received data for push notification: {data}")
        try:
            expo_ids = await self.push_token_service.get_team_player_tokens(
                team_id=team_id
            )
            logging.debug(f"Expo IDs: {expo_ids}")
            push_messages = [
                PushMessage(
                    to=token,
                    title="New Message From Your Coach !!",
                    body="Check it out",
                    data=data,
                    sound="default",
                    ttl=0,
                    expiration=None,
                    priority="default",
                    badge=None,
                    category="EventDetailPage",
                    channel_id=None,
                    subtitle=None,
                    mutable_content=False,
                )
                for token in expo_ids
            ]
            push_tickets = await push_client.publish_multiple(push_messages)
            return {"status": "Success", "ticket": push_tickets}

        except Exception as e:
            logging.error(f"Failed to process push notification: {str(e)}")

    def _on_connection_closed(self, _: Any, __: AMQPConnectionError):
        """Handle unexpectedly closed connection events."""
        logging.warning("RabbitMQ connection closed.")
        self.connection = None

    async def _on_connection_reconnected(self, connection: RobustConnection):
        """Handle reconnection events."""
        logging.info("RabbitMQ connection reconnected.")
        self.connection = connection

    async def _initiate_communication(self):
        """Establish communication with RabbitMQ (connection + channel)."""
        loop = asyncio.get_running_loop()
        self.connection = await connect_robust(loop=loop, url=self.rabbit_url)
        self.connection.reconnect_callbacks.add(self._on_connection_reconnected)
        self.connection.close_callbacks.add(self._on_connection_closed)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name, ExchangeType.TOPIC, durable=True
        )
        await self.channel.set_qos(prefetch_count=1)
        logging.info("RabbitMQ communication established with channel and exchange.")

    async def declare_and_bind_queue(self, queue_name: str, routing_keys: list):
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized.")
        queue = await self.channel.declare_queue(queue_name, durable=True)
        for routing_key in routing_keys:
            await queue.bind(self.exchange_name, routing_key)
            logging.info(
                f"Declared and bound queue {queue_name} to exchange {self.exchange_name} with routing key {routing_key}."
            )
        return queue

    async def publish_message(self, routing_key: str, message: dict):
        """Publish a message with specific routing keys."""
        if hasattr(message, "dict"):
            message = message.dict()
        body = json.dumps(message, indent=4, sort_keys=True, default=str).encode()
        msg = Message(
            body, content_type="application/json", delivery_mode=DeliveryMode.PERSISTENT
        )
        await self.exchange.publish(msg, routing_key=routing_key)
        logging.info(f"Message published to {routing_key}")

    async def initialize_existing_queues(self, teams):
        """Initialize existing queues based on team data."""
        for team in teams:
            queue_name = str(team["_id"])
            routing_keys = [
                f"team.{team['_id']}.event.*",
                f"team.{team['_id']}.notifications.*",
            ]
            await self.declare_and_bind_queue(queue_name, routing_keys)

    async def start_consumer(self, queue_name: str):
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized.")
        queue = await self.channel.declare_queue(
            queue_name, passive=True
        )  # Ensure the queue exists
        await queue.consume(self._process_incoming_message, no_ack=False)
        logging.info(f"Started consuming from {queue_name}")

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return False if self.connection is None else not self.connection.is_closed

    async def start(self):
        """Start the RabbitMQ client."""
        await self._initiate_communication()

    async def stop(self):
        """Stop the RabbitMQ client."""
        if self.connection:
            await self.connection.close()
