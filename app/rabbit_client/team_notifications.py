from ..utils import setup_logger

logging = setup_logger(__name__)


class TeamNotificationsMixin:
    async def handle_team_notification(self, team_id: str, event_data: dict):
        logging.info(f"Handling team event for team {team_id}")
        # Get team members' tokens
        team_tokens = await self.push_token_service.get_team_player_tokens(team_id)
        notification = event_data.get("body")
        title = notification["title"]
        # Prepare the notification
        body = event_data.get("description", "A new team event has occurred")
        data = {"event_id": event_data.get("id"), "team_id": team_id}

        # Send push notifications to team members
        await self.send_push_notifications(team_tokens, title, body, data)
