from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, EmailStr, Field, StringConstraints

from app.utils.dates import dt_to_iso


class Preferences(BaseModel):
    show_tips: bool = True
    default_view: Literal["workouts", "exercises"] = "workouts"
    theme: Literal["light", "dark", "system"] = "light"
    units: Literal["metric", "imperial"] = "metric"
    # allows arbitrary extra keys
    model_config = {"extra": "allow"}


DisplayNameStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class UserProfile(BaseModel):
    PK: str
    SK: Literal["PROFILE"]

    display_name: DisplayNameStr
    email: EmailStr

    created_at: datetime
    updated_at: datetime
    timezone: str = Field(..., min_length=1)

    preferences: Preferences = Preferences()

    def model_post_validate(self):
        if self.timezone not in available_timezones():
            raise ValueError(f"Invalid timezone: {self.timezone}")
        return self

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data
