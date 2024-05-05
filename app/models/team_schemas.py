from pydantic import BaseModel, Field
from typing import List


class CreateTeamSchema(BaseModel):
    team_id: str = Field(..., example="team123")
    team_name: str = Field(..., example="Warriors")
    team_players: List[str] = Field(..., example=["player1", "player2"])
    team_coaches: List[str] = Field(..., example=["coach1", "coach2"])
