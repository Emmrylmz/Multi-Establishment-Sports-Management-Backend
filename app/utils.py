from passlib.context import CryptContext
from bson import ObjectId
import json
import datetime
import logging
import sys
from typing import Any

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)


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


def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = logging.FileHandler("app.log")
    c_handler.setLevel(logging.DEBUG)
    f_handler.setLevel(logging.ERROR)

    # Create formatters and add it to handlers
    c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def convert_to_json_serializable(obj: Any) -> Any:
    logger.debug(f"Converting object of type: {type(obj)}")
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {
            str(convert_to_json_serializable(key)): convert_to_json_serializable(value)
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_to_json_serializable(item) for item in obj)
    elif isinstance(obj, set):
        return {convert_to_json_serializable(item) for item in obj}
    else:
        logger.debug(f"Returning object as-is: {obj}")
        return obj


def custom_json_dumps(obj: Any) -> str:
    import json

    return json.dumps(convert_to_json_serializable(obj))
