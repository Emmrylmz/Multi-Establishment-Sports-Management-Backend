import asyncio
from typing import Optional, Any, List
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
from fastapi import Request
from ..tools.ExponentServerSDK import push_client, PushMessage
from ..service.TokenService import PushTokenService
from ..service.TeamService import TeamService

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
            message_body = message.body.decode()
            data = json.loads(message_body)
            routing_key = message.routing_key

            logging.info(f"Received message with routing key: {routing_key}")
            logging.debug(f"Message body: {message_body}")

            if routing_key.startswith("team."):
                team_id = routing_key.split(".")[1]
                event = data.get("event")
                await self.handle_push_notification("team", event, team_id)
            elif routing_key.startswith("user."):
                user_id = data.get("user_id")
                notification = data.get("notification")
                await self.handle_push_notification("individual", notification, user_id)
            elif routing_key == "all.users.notification":
                notification = data.get("notification")
                await self.handle_push_notification("all_users", notification)
            elif routing_key.startswith("province."):
                province_id = routing_key.split(".")[1]
                notification = data.get("notification")
                await self.handle_push_notification(
                    "province", notification, province_id
                )
            else:
                logging.warning(
                    f"Received message with unknown routing key: {routing_key}"
                )

            logging.debug(f"Processed the message: {data}")
            await message.ack()

        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e} - Message Body: {message_body}")
        except Exception as e:
            logging.error(f"Failed to process message: {str(e)}")
        finally:
            logging.debug("Finished processing message")

    async def handle_push_notification(
        self, notification_type: str, data: Any, id: Optional[str] = None
    ):
        try:
            if notification_type == "team":
                await self.handle_team_event(id, data)
            elif notification_type == "individual":
                await self.send_individual_push_notification(
                    id, data["title"], data["body"], data.get("data", {})
                )
            elif notification_type == "all_users":
                await self.send_all_users_push_notification(
                    data["title"], data["body"], data.get("data", {})
                )
            elif notification_type == "province":
                await self.send_province_push_notification(
                    id, data["title"], data["body"], data.get("data", {})
                )
            else:
                logging.warning(f"Unknown notification type: {notification_type}")
        except Exception as e:
            logging.error(
                f"Failed to handle {notification_type} push notification: {str(e)}"
            )

    async def handle_team_event(self, team_id: str, event_data: dict):
        logging.info(f"Handling team event for team {team_id}")
        # Get team members' tokens
        team_tokens = await self.push_token_service.get_team_player_tokens(team_id)

        # Prepare the notification
        title = f"Team Event: {event_data.get('title', 'New Event')}"
        body = event_data.get("description", "A new team event has occurred")
        data = {"event_id": event_data.get("id"), "team_id": team_id}

        # Send push notifications to team members
        await self.send_push_notifications(team_tokens, title, body, data)

    async def send_individual_push_notification(
        self, user_id: str, title: str, body: str, data: dict
    ):
        logging.info(f"Sending individual push notification to user {user_id}")
        user_token = await self.push_token_service.get_user_token(user_id)
        if user_token:
            await self.send_push_notifications([user_token], title, body, data)
        else:
            logging.warning(f"No push token found for user {user_id}")

    async def send_all_users_push_notification(self, title: str, body: str, data: dict):
        logging.info("Sending push notification to all users")
        all_tokens = await self.push_token_service.get_all_user_tokens()
        await self.send_push_notifications(all_tokens, title, body, data)

    async def send_province_push_notification(
        self, province_id: str, title: str, body: str, data: dict
    ):
        logging.info(f"Sending push notification to users in province {province_id}")
        province_tokens = await self.push_token_service.get_by_province(
            province=province_id
        )
        await self.send_push_notifications(province_tokens, title, body, data)

    async def send_push_notifications(
        self, tokens: List[str], title: str, body: str, data: dict
    ):
        push_messages = [
            PushMessage(
                to=token,
                title=title,
                body=body,
                data=data,
                sound="default",
                ttl=0,
                expiration=None,
                priority="default",
                badge=None,
                category=None,
                channel_id=None,
                subtitle=None,
                mutable_content=False,
            )
            for token in tokens
        ]
        try:
            push_tickets = await push_client.publish_multiple(push_messages)
            logging.info(f"Push notifications sent. Tickets: {push_tickets}")
        except Exception as e:
            logging.error(f"Failed to send push notifications: {str(e)}")

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

    async def publish_individual_notification(
        self, user_id: str, title: str, body: str, data: dict
    ):
        """Publish an individual notification message to RabbitMQ."""
        message = {
            "user_id": user_id,
            "notification": {"title": title, "body": body, "data": data},
        }
        routing_key = f"user.{user_id}.notification"
        await self.publish_message(routing_key, message)

    async def initialize_queues(self, teams, provinces):
        """Initialize queues for teams, individual notifications, all users, and provinces."""
        # Initialize team queues
        for team in teams:
            queue_name = f"team_{team['_id']}"
            routing_keys = [
                f"team.{team['_id']}.event.*",
                f"team.{team['_id']}.notifications.*",
            ]
            await self.declare_and_bind_queue(queue_name, routing_keys)

        # Initialize individual notifications queue
        individual_queue_name = "individual_notifications"
        individual_routing_key = "user.*.notification"
        await self.declare_and_bind_queue(
            individual_queue_name, [individual_routing_key]
        )

        # Initialize all users notifications queue
        all_users_queue_name = "all_users_notifications"
        all_users_routing_key = "all.users.notification"
        await self.declare_and_bind_queue(all_users_queue_name, [all_users_routing_key])

        # Initialize province notifications queues
        for province in provinces:
            province_queue_name = f"province_{province['_id']}_notifications"
            province_routing_key = f"province.{province['_id']}.notification"
            await self.declare_and_bind_queue(
                province_queue_name, [province_routing_key]
            )

    async def start_consumers(self):
        """Start consumers for all queue types."""
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized.")

        # Define queue configurations
        queue_configs = [
            {
                "prefix": "all_users",
                "routing_key": "all.users.notification",
                "durable": True,
            },
            {"prefix": "team", "routing_key": "team.*.event.*", "durable": True},
            {
                "prefix": "province",
                "routing_key": "province.*.notification",
                "durable": True,
            },
            {
                "prefix": "individual",
                "routing_key": "user.*.notification",
                "durable": True,
            },
        ]

        for config in queue_configs:
            try:
                # Create a unique queue name for each prefix without using wildcards
                queue_name = f"{config['prefix']}_queue"

                # Declare the queue
                queue = await self.channel.declare_queue(
                    queue_name, durable=config["durable"]
                )

                # Bind the queue to the exchange with the appropriate routing key
                await queue.bind(self.exchange_name, routing_key=config["routing_key"])

                # Start consuming from this queue
                await queue.consume(self._process_incoming_message, no_ack=False)

                logging.info(f"Started consumer for {config['prefix']} queues")

            except Exception as e:
                logging.error(
                    f"Failed to start consumer for {config['prefix']} queues: {str(e)}"
                )

        logging.info("Started consumers for all queue types")

    async def create_team_queue(self, team_id: str):
        """Create and start consuming from a team-specific queue."""
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized.")

        queue_name = f"team_{team_id}_queue"
        team_queue = await self.channel.declare_queue(queue_name, durable=True)
        await team_queue.bind(self.exchange_name, routing_key=f"team.{team_id}.#")
        await team_queue.consume(self._process_incoming_message)

        logging.info(f"Created and started consuming from team queue: {queue_name}")

    async def publish_all_users_notification(self, title: str, body: str, data: dict):
        """Publish a notification for all users."""
        message = {"notification": {"title": title, "body": body, "data": data}}
        routing_key = "all.users.notification"
        await self.publish_message(routing_key, message)

    async def publish_province_notification(
        self, province_id: str, title: str, body: str, data: dict
    ):
        """Publish a notification for users in a specific province."""
        message = {
            "province_id": province_id,
            "notification": {"title": title, "body": body, "data": data},
        }
        routing_key = f"province.{province_id}.notification"
        await self.publish_message(routing_key, message)

    async def send_all_users_push_notification(self, title: str, body: str, data: dict):
        """Send push notification to all users."""
        logging.debug("Sending push notification to all users")
        try:
            # Get all user tokens
            all_tokens = await self.push_token_service.get_all_user_tokens()

            push_messages = [
                PushMessage(
                    to=token,
                    title=title,
                    body=body,
                    data=data,
                    sound="default",
                    ttl=0,
                    expiration=None,
                    priority="default",
                    badge=None,
                    category="AllUsersNotification",
                    channel_id=None,
                    subtitle=None,
                    mutable_content=False,
                )
                for token in all_tokens
            ]
            push_tickets = await push_client.publish_multiple(push_messages)
            return {"status": "Success", "ticket": push_tickets}

        except Exception as e:
            logging.error(f"Failed to send all users push notification: {str(e)}")
            return {"status": "Failed", "reason": str(e)}

    async def send_province_push_notification(
        self, province_id: str, title: str, body: str, data: dict
    ):
        """Send push notification to users in a specific province."""
        logging.debug(f"Sending push notification to users in province: {province_id}")
        try:
            # Get tokens for users in the specified province
            province_tokens = await self.push_token_service.get_province_user_tokens(
                province_id
            )

            push_messages = [
                PushMessage(
                    to=token,
                    title=title,
                    body=body,
                    data=data,
                    sound="default",
                    ttl=0,
                    expiration=None,
                    priority="default",
                    badge=None,
                    category="ProvinceNotification",
                    channel_id=None,
                    subtitle=None,
                    mutable_content=False,
                )
                for token in province_tokens
            ]
            push_tickets = await push_client.publish_multiple(push_messages)
            return {"status": "Success", "ticket": push_tickets}

        except Exception as e:
            logging.error(f"Failed to send province push notification: {str(e)}")
            return {"status": "Failed", "reason": str(e)}

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
