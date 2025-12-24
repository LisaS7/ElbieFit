from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.utils.dates import dt_to_iso

DisplayNameStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
Theme = Literal["light", "dark", "system"]
Units = Literal["metric", "imperial"]
WeightUnit = Literal["kg", "lb"]
ProfileSK = Literal["PROFILE"]


class Preferences(BaseModel):
    show_tips: bool = True
    theme: Theme = "light"
    units: Units = "metric"
    # allows arbitrary extra keys
    model_config = {"extra": "allow"}


class UserProfile(BaseModel):
    PK: str
    SK: ProfileSK

    display_name: DisplayNameStr
    email: EmailStr

    created_at: datetime
    updated_at: datetime
    timezone: str = Field(..., min_length=1)

    preferences: Preferences = Preferences()

    @model_validator(mode="after")
    def validate_timezone(self) -> "UserProfile":
        if self.timezone not in available_timezones():
            raise ValueError(f"Invalid timezone: {self.timezone}")
        return self

    @property
    def weight_unit(self) -> Literal["kg", "lb"]:
        return "lb" if self.preferences.units == "imperial" else "kg"

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data


class AccountUpdateForm(BaseModel):
    display_name: DisplayNameStr
    timezone: str = Field(..., min_length=1)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in available_timezones():
            raise ValueError(f"Invalid timezone: {v}")
        return v


class PreferencesUpdateForm(BaseModel):
    show_tips: bool = False
    theme: Theme
    units: Units
