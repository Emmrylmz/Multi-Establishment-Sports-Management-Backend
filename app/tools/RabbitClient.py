import asyncio
import json
from aio_pika import connect_robust, Message, ExchangeType, DeliveryMode
from datetime import datetime
import logging

class DateTimeEncoder(json.JSONEncoder):
    """ Custom JSON encoder for datetime objects """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class RabbitClient:
    """Handles setup and interaction with RabbitMQ for various notification types."""

    def __init__(self, rabbit_url: str, exchange_name: str = "notifications_exchange12"):
        self.rabbit_url = rabbit_url
        self.exchange_name = exchange_name
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        """Connect and setup the primary exchange."""
        self.connection = await connect_robust(self.rabbit_url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(self.exchange_name, ExchangeType.TOPIC, durable=True)
        await self.channel.set_qos(prefetch_count=1)
        logging.info(f"Connected to {self.exchange_name} at {self.rabbit_url}")

    async def declare_and_bind_queue(self, queue_name: str, routing_keys: list):
        """Declare a new queue and bind it with specific routing keys."""
        queue = await self.channel.declare_queue(queue_name, durable=True)
        for routing_key in routing_keys:
            await queue.bind(self.exchange, routing_key=routing_key)
        logging.info(f"Queue {queue_name} declared and bound with routing keys: {routing_keys}")

    async def publish_message(self, routing_key: str, message: dict):
        """Publish a message with specific routing keys."""
        if hasattr(message, 'dict'):
            message = message.dict()
        body = json.dumps(message, cls=DateTimeEncoder).encode() 
        msg = Message(body, content_type='application/json', delivery_mode=DeliveryMode.PERSISTENT)
        await self.exchange.publish(msg, routing_key=routing_key)
        logging.info(f"Message published to {routing_key}")


    async def start_consumer(self, queue_name: str, callback):
        """Start consuming messages from a specified queue."""
        queue = await self.channel.get_queue(queue_name)
        await queue.consume(callback)
        logging.info(f"Started consuming from {queue_name}")

    async def close(self):
        """Close the connection."""
        await self.connection.close()
        logging.info("RabbitMQ connection closed")

async def message_handler(message):
    """Process incoming messages."""
    with message.process():
        data = json.loads(message.body.decode())
        logging.info(f"Received: {data}")