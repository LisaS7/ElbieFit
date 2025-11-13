from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

from app.utils.dates import dt_to_iso


class Preferences(BaseModel):
    show_tips: bool = True
    default_view: str = "workouts"
    theme: str = "light"
    units: Literal["metric", "imperial"] = "metric"
    # allows arbitrary extra keys
    model_config = {"extra": "allow"}


class UserProfile(BaseModel):
    PK: str
    SK: Literal["PROFILE"]
    display_name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    preferences: Preferences = Preferences()
    timezone: str

    def to_ddb_item(self) -> dict:
        data = self.model_dump()
        data["created_at"] = dt_to_iso(self.created_at)
        data["updated_at"] = dt_to_iso(self.updated_at)
        return data
