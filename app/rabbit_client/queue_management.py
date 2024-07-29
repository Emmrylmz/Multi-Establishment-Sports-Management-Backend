from ..utils import setup_logger

logging = setup_logger(__name__)


class QueueManagementMixin:
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
        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized.")

        queue_configs = [
            {
                "prefix": "global",
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
            queue_name = f"{config['prefix']}_queue"
            queue = await self.channel.declare_queue(
                queue_name, durable=config["durable"]
            )
            await queue.bind(self.exchange, routing_key=config["routing_key"])
            await queue.consume(self._process_incoming_message)
            logging.info(f"Started consumer for {config['prefix']} queue")
