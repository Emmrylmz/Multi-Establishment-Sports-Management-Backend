def userResponseEntity(user) -> dict:

    return {
        "id": str(user["_id"]),
        "name": user.get("name", None),
        "email": contact_info.get(
            "email", None
        ),  # Safely get the email from contact_info
        "photo": user.get("photo", None),
        "role": user.get("role", None),
        "created_at": user.get("created_at", None),
    }


def embedded_user_response(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user.get("name", None),
        "email": user.get("contact_info", {}).get("email", None),
        "photo": user.get("photo", None),
    }


def user_list_entity(users) -> list:
    return [userEntity(user) for user in users]
