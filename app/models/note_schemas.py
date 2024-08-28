from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum
from .user_schemas import UserRole


class NoteType(str, Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"
    PROVINCE = "province"
    GLOBAL = "global"


class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_announcement: bool = False


class NoteCreate(NoteBase):
    note_type: NoteType
    recipient_id: Optional[str]  # For individual notes
    team_id: Optional[str]  # For team notes
    province_id: Optional[str]  # For province notes


class NoteInDB(NoteBase):
    id: str = None
    author_id: str
    note_type: NoteType
    recipient_id: Optional[str]
    team_id: Optional[str]
    province_id: Optional[str]


class NoteResponse(NoteInDB):
    pass


class NoteList(BaseModel):
    notes: List[NoteResponse]
    total: int
