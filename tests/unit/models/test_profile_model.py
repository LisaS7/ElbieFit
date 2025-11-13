from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.profile import Preferences, UserProfile

# ---------- Preferences ----------


def test_preferences_defaults():
    prefs = Preferences()

    assert prefs.show_tips is True
    assert prefs.default_view == "workouts"
    assert prefs.theme == "light"
    assert prefs.units == "metric"


def test_preferences_invalid_units_raises():
    with pytest.raises(ValidationError):
        Preferences(units="goblin")  # type: ignore


# ---------- UserProfile ----------


def _base_profile_kwargs():
    return {
        "PK": "USER#123",
        "SK": "PROFILE",
        "display_name": "Lisa Test",
        "email": "lisa@example.com",
        "created_at": datetime(2025, 1, 1, 12, 0, 0),
        "updated_at": datetime(2025, 1, 1, 13, 0, 0),
        "timezone": "Europe/London",
    }


def test_user_profile_valid_instance_and_default_preferences():
    profile = UserProfile(**_base_profile_kwargs())

    assert profile.PK == "USER#123"
    assert profile.SK == "PROFILE"
    assert profile.display_name == "Lisa Test"
    assert profile.email == "lisa@example.com"

    # created/updated are parsed as datetime
    assert isinstance(profile.created_at, datetime)
    assert isinstance(profile.updated_at, datetime)

    # preferences should be a Preferences instance with defaults
    assert isinstance(profile.preferences, Preferences)
    assert profile.preferences.units == "metric"
    assert profile.preferences.show_tips is True


def test_user_profile_requires_sk_profile_literal():
    kwargs = _base_profile_kwargs()
    kwargs["SK"] = "NOT_PROFILE"

    with pytest.raises(ValidationError):
        UserProfile(**kwargs)


def test_user_profile_validates_email():
    kwargs = _base_profile_kwargs()
    kwargs["email"] = "not-an-email"

    with pytest.raises(ValidationError):
        UserProfile(**kwargs)


def test_to_ddb_item_serializes_datetimes_and_nests_preferences():
    profile = UserProfile(**_base_profile_kwargs())
    ddb_item = profile.to_ddb_item()

    # top-level keys preserved
    assert ddb_item["PK"] == "USER#123"
    assert ddb_item["SK"] == "PROFILE"
    assert ddb_item["display_name"] == "Lisa Test"
    assert ddb_item["email"] == "lisa@example.com"
    assert ddb_item["timezone"] == "Europe/London"

    # datetimes should have been converted to strings by dt_to_iso
    assert isinstance(ddb_item["created_at"], str)
    assert isinstance(ddb_item["updated_at"], str)

    # preferences should be a nested dict, not a model instance
    prefs = ddb_item["preferences"]
    assert isinstance(prefs, dict)
    assert prefs["units"] == "metric"
    assert prefs["default_view"] == "workouts"
