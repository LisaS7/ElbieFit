from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.utils.dates import dt_to_iso


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
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data
