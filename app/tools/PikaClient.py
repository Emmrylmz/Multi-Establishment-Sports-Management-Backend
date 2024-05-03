import json
import uuid
import logging
import pika
from pika import connection
from asgiref.sync import async_to_sync
from aio_pika import connect_robust, Message

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PikaClient:
    def __init__(self, process_callable):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=5672, heartbeat=600)
        )
        self.channel = self.connection.channel()
        self.process_callable = process_callable
        logger.info("Pika connection initialized")

    def declare_queue(self, queue_name):
        """Dynamically declare a new queue"""
        queue_result = self.channel.queue_declare(queue=queue_name, durable=True)
        return queue_result.method.queue

    async def consume(self, loop, queue_name):
        """Setup message listener for a specific queue with the current running loop"""
        connection = await connect_robust(host="localhost", port=5672, loop=loop)
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name)
        await queue.consume(self.process_incoming_message, no_ack=False)
        logger.info(f"Established pika async listener on {queue_name}")
        return connection

    async def process_incoming_message(self, message):
        """Processing incoming message from RabbitMQ"""
        body = message.body
        logger.info("Received message")
        if body:
            try:
                data = json.loads(body)
                self.process_callable(data)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}")
        else:
            logger.warning("Received an empty message")

    def send_message(self, message: dict, routing_key):
        """Method to publish message to RabbitMQ"""
        self.channel.basic_publish(
            exchange="",
            routing_key=routing_key,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue, correlation_id=str(uuid.uuid4())
            ),
            body=json.dumps(message, indent=4, sort_keys=True, default=str),
        )

    def close(self):
        """Close the Pika connection"""
        self.connection.close()
        logger.info("Pika connection closed")
