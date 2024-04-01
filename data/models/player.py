from pydantic import BaseModel
from typing import Optional

class Player(BaseModel):
    playerName: Optional[str] = None
    playerAge: Optional[int] = None
    playerHeight: Optional[float] = None
    playerWeight: Optional[float] = None

    
    