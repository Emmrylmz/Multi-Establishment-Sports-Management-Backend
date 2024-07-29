from typing import List, Optional
from ..tools.ExponentServerSDK import push_client, PushMessage
from ..utils import setup_logger

logging = setup_logger(__name__)


class PushNotificationsMixin:
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

    async def send_individual_push_notification(
        self, user_id: str, title: str, body: str, data: dict
    ):
        logging.info(f"Sending individual push notification to user {user_id}")
        user_token = await self.push_token_service.get_user_token(user_id)
        if user_token:
            await self.send_push_notifications([user_token], title, body, data)
        else:
            logging.warning(f"No push token found for user {user_id}")

    async def send_all_users_push_notification(
        self, title: str, body: str, data: Optional[dict] = None
    ):
        logging.debug("Sending push notification to all users")
        try:
            # Get all user tokens
            all_tokens = await self.push_token_service.get_all_user_tokens()

            push_messages = [
                PushMessage(
                    to=token,
                    title=title,
                    body=body,
                    data=data or {},  # Use an empty dict if data is None
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
