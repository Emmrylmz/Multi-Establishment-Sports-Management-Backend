
def userEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user.get("name", None),
        "email": user.get("email", None),  # Safely access nested fields
        "password": user.get("password"),
        "photo": user.get("photo", None),
        "role": user.get("role", None),
        "teams": user.get("teams", []),
        "created_at": user.get("created_at", None),
        "personal_attributes": user.get("personal_attributes", None),
        "family_contacts": user.get("family_contacts", [])  # Assumes list of contact dictionaries
    }

def userResponseEntity(user) -> dict:
    contact_info = user.get("contact_info") or {}
    
    return {
        "id": str(user["_id"]),
        "name": user.get("name", None),
        "email": contact_info.get("email", None),  # Safely get the email from contact_info
        "photo": user.get("photo", None),
        "role": user.get("role", None),
        "created_at": user.get("created_at", None)
    }

def embedded_user_response(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user.get("name", None),
        "email": user.get("contact_info", {}).get("email", None),
        "photo": user.get("photo", None)
    }

def user_list_entity(users) -> list:
    return [user_entity(user) for user in users]