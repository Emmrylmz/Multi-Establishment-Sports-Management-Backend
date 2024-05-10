from pydantic import BaseModel, EmailStr, validator, constr, Field
from typing import List, Optional, Literal
from datetime import datetime


class NotificationRequest(BaseModel):
    token: str
    title: str
    body: str
    data: dict = None
