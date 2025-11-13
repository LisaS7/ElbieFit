from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.utils.dates import dt_to_iso


class Workout(BaseModel):
    PK: str
    SK: str  # "WORKOUT#2025-11-04#W1"
    type: Literal["workout"]
    date: date
    tags: list[str]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data


class WorkoutSet(BaseModel):
    PK: str
    SK: str  # "WORKOUT#...#SET#001"
    type: Literal["set"]
    exercise_id: str
    set_number: int
    reps: int
    weight_kg: float
    rpe: int
    created_at: datetime
    updated_at: datetime

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data
