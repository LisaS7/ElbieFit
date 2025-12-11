from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints

from app.utils.dates import dt_to_iso

NameStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

MuscleStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]

EquipmentStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]

CategoryStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class Exercise(BaseModel):
    PK: str
    SK: str  # "EXERCISE#<uuid>"
    type: Literal["exercise"]

    name: NameStr
    muscles: list[MuscleStr] = Field(min_length=1)
    equipment: EquipmentStr
    category: Optional[CategoryStr] = None

    created_at: datetime
    updated_at: datetime

    @property
    def exercise_id(self) -> str:
        return self.SK.split("#")[-1]

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data
