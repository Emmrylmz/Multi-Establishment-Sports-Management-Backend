import json
from aio_pika import IncomingMessage
from ..models.note_schemas import NoteType
from typing import Any, Optional
from ..utils import setup_logger

logger = setup_logger(__name__)


class MessageProcessingMixin:
    async def _process_incoming_message(self, message: IncomingMessage):
        logger.debug("Starting message processing")
        try:
            message_body = message.body.decode()
            data = json.loads(message_body)
            routing_key = message.routing_key

            logger.info(f"Received message with routing key: {routing_key}")
            logger.debug(f"Message body: {message_body}")

            if routing_key.startswith("team."):
                team_id = routing_key.split(".")[1]
                event = data
                await self.handle_push_notification(NoteType.TEAM, event, team_id)
            elif routing_key.startswith("user."):
                user_id = data.get("user_id")
                notification = data.get("notification")
                await self.handle_push_notification(
                    NoteType.INDIVIDUAL, notification, user_id
                )
            elif routing_key == "all.users.notification":
                await self.handle_push_notification(NoteType.GLOBAL, data)
            elif routing_key.startswith("province."):
                province_id = routing_key.split(".")[1]
                notification = data.get("notification")
                await self.handle_push_notification(
                    NoteType.PROVINCE, notification, province_id
                )
            else:
                logger.warning(
                    f"Received message with unknown routing key: {routing_key}"
                )

            logger.debug(f"Processed the message: {data}")
            await message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e} - Message Body: {message_body}")
            await message.reject(requeue=False)
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            await message.reject(requeue=True)
        finally:
            logger.debug("Finished processing message")

    async def handle_push_notification(
        self, notification_type: NoteType, data: Any, id: Optional[str] = None
    ):
        try:
            if notification_type == NoteType.TEAM:
                if hasattr(self, "handle_team_notification"):
                    await self.handle_team_notification(id, data)
                else:
                    logger.error("handle_team_notification method not implemented")
            elif notification_type == NoteType.INDIVIDUAL:
                if isinstance(data, dict) and "title" in data and "body" in data:
                    await self.send_individual_push_notification(
                        id, data["title"], data["body"], data.get("data", {})
                    )
                else:
                    logger.error(
                        f"Invalid data format for individual notification: {data}"
                    )
            elif notification_type == NoteType.GLOBAL:
                if data is None:
                    logger.error("No data provided for global notification")
                    return
                if isinstance(data, dict):
                    body_data = data.get("body", {})
                    if isinstance(body_data, dict):
                        title = body_data.get("title", "Global Notification")
                        content = body_data.get("content", "")
                        additional_data = {
                            k: v
                            for k, v in body_data.items()
                            if k not in ["title", "content"]
                        }
                        await self.send_all_users_push_notification(
                            title, content, additional_data
                        )
                    else:
                        logger.error(
                            f"Invalid body format for global notification: {body_data}"
                        )
                else:
                    logger.error(f"Invalid data format for global notification: {data}")
            elif notification_type == NoteType.PROVINCE:
                if isinstance(data, dict) and "body" in data:
                    body_data = data["body"]
                    title = body_data.get("title", "Province Notification")
                    content = body_data.get("content", "")
                    additional_data = {
                        k: v
                        for k, v in body_data.items()
                        if k not in ["title", "content"]
                    }
                    await self.send_province_push_notification(
                        id, title, content, additional_data
                    )
                else:
                    logger.error(
                        f"Invalid data format for province notification: {data}"
                    )
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
        except Exception as e:
            logger.error(
                f"Failed to handle {notification_type} push notification: {str(e)}"
            )
