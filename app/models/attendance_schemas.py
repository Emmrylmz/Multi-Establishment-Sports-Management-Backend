from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


class AttendanceRecord(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    status: AttendanceStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AttendanceFormSchema(BaseModel):
    event_id: str
    attendances: List[AttendanceRecord]


class FetchAttendanceFromEventIdSchema(BaseModel):
    event_id: str


class FetchAttendanceFromEventIdResponseSchema(BaseModel):
    attendances: List[AttendanceRecord]
    has_next: bool
    next_cursor: Optional[str]


class UpdateAttendanceSchema(BaseModel):
    event_id: str
    attendances: List[AttendanceRecord]
