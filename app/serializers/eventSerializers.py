def eventEntity(event) -> dict:

    return {
        "id": str(event["_id"]),
        "name": event.get("name", None),
        "description": event.get("description", None),
        "team_id": event.get("team_id", None),
        "created_at": event.get("created_at", None),
        "event_date": event.get("event_date", None),
        "type": event.get("type", None),
    }


def eventResponseEntity(user) -> dict:

    return {
        "name": event.get("name", None),
        "event_date": event.get("event_date", None),
        "created_at": user.get("created_at", None),
    }


def user_list_entity(events) -> list:
    return [eventEntity(event) for event in events]
