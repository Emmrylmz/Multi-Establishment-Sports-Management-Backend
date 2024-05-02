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
        self.publish_queue_name = "abs"
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=5672, heartbeat=600)
        )
        self.channel = self.connection.channel()
        queue_result = self.channel.queue_declare(queue=self.publish_queue_name)
        self.callback_queue = queue_result.method.queue
        self.process_callable = process_callable
        logger.info("Pika connection initialized")

    async def consume(self, loop):
        """Setup message listener with the current running loop"""
        connection = await connect_robust(host="localhost", port=5672, loop=loop)
        channel = await connection.channel()
        queue = await channel.declare_queue(self.publish_queue_name)
        await queue.consume(self.process_incoming_message, no_ack=False)
        logger.info("Established pika async listener")
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

    def send_message(self, message: dict):
        """Method to publish message to RabbitMQ"""
        self.channel.basic_publish(
            exchange="",
            routing_key=self.publish_queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue, correlation_id=str(uuid.uuid4())
            ),
            body=json.dumps(message, indent=4, sort_keys=True, default=str),
        )

    def close(self):
        """Close the Pika connection"""
        self.connection.close()
        logger.info("Pika connection closed")


# Example usage of PikaClient with a dummy callable function
if __name__ == "__main__":

    def process_message(data):
        print("Processing:", data)

    client = PikaClient(process_message)
    client.send_message({"key": "value"})
    client.close()
