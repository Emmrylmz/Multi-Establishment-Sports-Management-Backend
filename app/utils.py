from passlib.context import CryptContext
from bson import ObjectId
import json
import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


def ensure_object_id(id):
    """
    Ensures that the provided identifier is an instance of ObjectId.
    Converts the identifier to ObjectId if it is not already.

    Parameters:
        id (str or ObjectId): The identifier to convert.

    Returns:
        ObjectId: The identifier converted to ObjectId, if necessary.
    """
    return ObjectId(id) if not isinstance(id, ObjectId) else id


class DateTimeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, type([datetime, datetime.date, datetime.time])):
            return obj.isoformat()
        elif isinstance(obj, type(datetime.timedelta)):
            return (datetime.datetime.min + obj).time().isoformat()
        return super(DateTimeEncoder, self).default(obj)
