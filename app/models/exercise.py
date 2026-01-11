from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.utils.dates import dt_to_iso
from app.utils.taxonomy import EQUIPMENT_TYPES, EXERCISE_CATEGORIES, MUSCLE_GROUPS

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


def _normalise_key(value: str) -> str:
    v = value.strip().lower()
    v = v.replace("-", "_").replace(" ", "_")
    return v


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

    # -------- Validators --------

    @field_validator("equipment")
    @classmethod
    def validate_equipment(cls, v: str) -> str:
        v = _normalise_key(v)
        if v not in EQUIPMENT_TYPES:
            allowed = ", ".join(EQUIPMENT_TYPES)
            raise ValueError(f"Invalid equipment '{v}'. Allowed: {allowed}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = _normalise_key(v)
        if v not in EXERCISE_CATEGORIES:
            allowed = ", ".join(EXERCISE_CATEGORIES)
            raise ValueError(f"Invalid category '{v}'. Allowed: {allowed}")
        return v

    @field_validator("muscles")
    @classmethod
    def validate_muscles(cls, v: list[str]) -> list[str]:
        normalized: list[str] = []
        for m in v:
            mm = _normalise_key(m)
            if mm not in MUSCLE_GROUPS:
                allowed = ", ".join(MUSCLE_GROUPS)
                raise ValueError(f"Invalid muscle '{mm}'. Allowed: {allowed}")
            normalized.append(mm)

        # de-dupe but keep order
        deduped = list(dict.fromkeys(normalized))
        return deduped

    # ----------------------------

    @property
    def exercise_id(self) -> str:
        return self.SK.split("#")[-1]

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data
