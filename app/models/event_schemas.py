from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class CreateEventSchema(BaseModel):
    event_id: str
    event_type: Literal["Game", "Training"]
    creator_id: str
    place: str
    event_date: datetime  # corrected from event_data
    created_at: datetime = Field(default_factory=datetime.now)
    team_id: str
    description: Optional[str]

    class Config:
        orm_mode = True


class CreateGameEventSchema(CreateEventSchema):
    opponent: str
