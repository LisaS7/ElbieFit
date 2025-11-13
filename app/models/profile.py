from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, EmailStr


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
        data["created_at"] = (
            self.created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        return data
