from typing import List
from pydantic import BaseModel
from datetime import datetime


class AttendanceRecord(BaseModel):
    user_id: str
    status: str


class AttendanceFormSchema(BaseModel):
    event_id: str
    event_type: str
    attendances: List[AttendanceRecord]


class FetchAttendanceFromEventIdSchema(BaseModel):
    event_id: str


class UpdateAttendanceSchema(BaseModel):
    attendances: List[AttendanceRecord]
    event_id: str
    event_type: str
