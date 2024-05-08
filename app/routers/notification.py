from fastapi import APIRouter
from ..tools.RabbitClient import RabbitClient
from ..tools.ExponentServerSDK import push_client, PushMessage
from ..models.notification_schemas import NotificationRequest

router = APIRouter(prefix="/api/notification", tags=["trigger_in"])


@router.post("/send_notification/")
async def send_notification(request: NotificationRequest):
    push_message = PushMessage(
        to=request.token,
        title=request.title,
        body=request.body,
        data=request.data or {},
    )

    try:
        # Send the notification
        ticket = push_client.publish(push_message)
        return {"status": "Success", "ticket": ticket}

    except Exception as e:
        # Catch any broad exceptions and return as HTTP error
        raise HTTPException(status_code=500, detail=str(e))
