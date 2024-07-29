from aio_pika import Message, DeliveryMode
import json
from ..utils import setup_logger

logging = setup_logger(__name__)


class MessagePublishingMixin:
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
