from typing import List
from pydantic import BaseModel
from datetime import datetime


class AttendanceRecord(BaseModel):
    user_id: str
    status: str


class AttendanceFormSchema(BaseModel):
    event_id: str
    event_type: str  # 'game' or 'training'
    team_id: str
    attendances: List[AttendanceRecord]
