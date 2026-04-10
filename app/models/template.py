from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import Form
from pydantic import BaseModel, Field, StringConstraints

from app.utils.dates import dt_to_iso

NameStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
TagStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class Template(BaseModel):
    PK: str
    SK: str  # "TEMPLATE#<uuid>"
    type: Literal["template"]
    name: NameStr
    tags: list[TagStr] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    created_at: datetime
    updated_at: datetime

    @property
    def template_id(self) -> str:
        return self.SK.split("#")[-1]

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data


class TemplateCreate(BaseModel):
    name: NameStr

    @classmethod
    def as_form(
        cls,
        name: Annotated[str, Form()],
    ) -> "TemplateCreate":
        return cls(name=name)


class TemplateUpdate(BaseModel):
    name: NameStr
    tags: list[TagStr] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @classmethod
    def as_form(
        cls,
        name: Annotated[str, Form()],
        notes: Annotated[str | None, Form()] = None,
        tags: Annotated[str | None, Form()] = None,
    ) -> "TemplateUpdate":
        tag_list: list[str] | None = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        return cls(name=name, notes=notes, tags=tag_list)


class TemplateSet(BaseModel):
    PK: str
    SK: str  # "TEMPLATE#<uuid>#SET#001"
    type: Literal["template_set"]
    exercise_id: str
    set_number: int
    reps: int | None = Field(default=None, ge=1)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    rpe: int | None = Field(default=None, ge=1, le=10)

    created_at: datetime
    updated_at: datetime

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        # Templates do NOT write ExercisePK/ExerciseSK GSI keys —
        # template sets must not appear in exercise history.
        return data


class TemplateSetBase(BaseModel):
    reps: int | None = Field(default=None, ge=1)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    rpe: int | None = Field(default=None, ge=1, le=10)


class TemplateSetCreate(TemplateSetBase):
    @classmethod
    def as_form(
        cls,
        reps: Annotated[str | None, Form()] = None,
        weight_kg: Annotated[str | None, Form()] = None,
        rpe: Annotated[str | None, Form()] = None,
    ) -> "TemplateSetCreate":
        return cls(
            reps=int(reps) if reps else None,
            weight_kg=Decimal(weight_kg) if weight_kg else None,
            rpe=int(rpe) if rpe else None,
        )


class TemplateSetUpdate(TemplateSetBase):
    @classmethod
    def as_form(
        cls,
        reps: Annotated[str | None, Form()] = None,
        weight_kg: Annotated[str | None, Form()] = None,
        rpe: Annotated[str | None, Form()] = None,
    ) -> "TemplateSetUpdate":
        return cls(
            reps=int(reps) if reps else None,
            weight_kg=Decimal(weight_kg) if weight_kg else None,
            rpe=int(rpe) if rpe else None,
        )
