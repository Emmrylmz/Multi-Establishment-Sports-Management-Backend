import asyncio
from typing import Any  # Add this import
from aio_pika import connect_robust, RobustConnection, ExchangeType
from aio_pika.exceptions import AMQPConnectionError
from ..utils import setup_logger

logging = setup_logger(__name__)


class ConnectionMixin:
    async def start(self):
        await self._initiate_communication()

    async def stop(self):
        if self.connection:
            await self.connection.close()

    async def _initiate_communication(self):
        loop = asyncio.get_running_loop()
        self.connection = await connect_robust(loop=loop, url=self.rabbit_url)
        self.connection.reconnect_callbacks.add(self._on_connection_reconnected)
        self.connection.close_callbacks.add(self._on_connection_closed)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name, ExchangeType.TOPIC, durable=True
        )
        await self.channel.set_qos(prefetch_count=1)

    def _on_connection_closed(self, _: Any, __: AMQPConnectionError):
        self.connection = None

    async def _on_connection_reconnected(self, connection: RobustConnection):
        self.connection = connection

    @property
    def is_connected(self) -> bool:
        return False if self.connection is None else not self.connection.is_closed
