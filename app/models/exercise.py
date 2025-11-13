from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class Exercise(BaseModel):
    PK: str
    SK: str  # "EXERCISE#E_PUSHUP"
    type: Literal["exercise"]
    name: str
    muscles: list[str]
    equipment: str
    category: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    def to_ddb_item(self) -> dict:
        return self.model_dump()
