from datetime import date as DateType
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import Form
from pydantic import BaseModel, Field, StringConstraints

from app.utils.dates import date_to_iso, dt_to_iso

NameStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
TagStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class Workout(BaseModel):
    PK: str
    SK: str  # "WORKOUT#2025-11-04#W1"
    type: Literal["workout"]
    date: DateType
    name: NameStr
    tags: list[TagStr] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    created_at: datetime
    updated_at: datetime

    @property
    def workout_id(self) -> str:
        return self.SK.split("#")[-1]

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["date"] = date_to_iso(self.date)
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data


class WorkoutCreate(BaseModel):
    date: DateType
    name: NameStr

    @classmethod
    def as_form(
        cls,
        date: Annotated[DateType, Form()],
        name: Annotated[str, Form()],
    ) -> "WorkoutCreate":
        return cls(date=date, name=name)


class WorkoutUpdate(BaseModel):
    date: DateType
    name: NameStr
    tags: list[TagStr] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @classmethod
    def as_form(
        cls,
        name: Annotated[str, Form()],
        date: Annotated[DateType, Form()],
        notes: Annotated[str | None, Form()] = None,
        tags: Annotated[str | None, Form()] = None,
    ):

        tag_list: list[str] | None = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        return cls(name=name, date=date, notes=notes, tags=tag_list)


class WorkoutSet(BaseModel):
    PK: str
    SK: str  # "WORKOUT#2025-11-04#W1#SET#001"
    type: Literal["set"]
    exercise_id: str
    set_number: int
    reps: int = Field(ge=1)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    rpe: int | None = Field(default=None, ge=1, le=10)  # Rate of Perceived Exertion

    created_at: datetime
    updated_at: datetime

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data

    @property
    def workout_id(self) -> str:
        parts = self.SK.split("#")
        if len(parts) < 3:
            raise ValueError(f"Invalid SK format: {self.SK}")
        return parts[2]


class WorkoutSetCreate(BaseModel):
    reps: int = Field(ge=1)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    rpe: int | None = Field(default=None, ge=1, le=10)

    @classmethod
    def as_form(
        cls,
        reps: Annotated[int, Form()],
        weight_kg: Annotated[Decimal | None, Form()] = None,
        rpe: Annotated[int | None, Form()] = None,
    ) -> "WorkoutSetCreate":
        return cls(
            reps=reps,
            weight_kg=weight_kg,
            rpe=rpe,
        )


class WorkoutSetUpdate(WorkoutSetCreate):
    pass
