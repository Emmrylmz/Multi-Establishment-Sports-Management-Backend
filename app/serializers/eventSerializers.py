def eventEntity(event) -> dict:

    return {
        "event_id": event.get("event_id", None),
        "event_type": event.get("event_type", None),
        "creator_id": event.get("creator_id", None),
        "description": event.get("description", None),
        "place": event.get("place", None),
        "team_id": event.get("team_id", None),
        "created_at": event.get("created_at", None),
        "event_date": event.get("event_date", None),
    }


def eventResponseEntity(user) -> dict:

    return {
        "name": event.get("name", None),
        "event_date": event.get("event_date", None),
        "description": event.get("description", None),
        "place": event.get("place", None),
        "event_type": event.get("event_type", None),
    }


def user_list_entity(events) -> list:
    return [eventEntity(event) for event in events]
