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


def test_user_profile_valid_instance_and_default_preferences(user_profile):
    assert user_profile.PK == "USER#123"
    assert user_profile.SK == "PROFILE"
    assert user_profile.display_name == "Lisa Test"
    assert user_profile.email == "lisa@example.com"

    # created/updated are parsed as datetime
    assert isinstance(user_profile.created_at, datetime)
    assert isinstance(user_profile.updated_at, datetime)

    # preferences should be a Preferences instance with defaults
    assert isinstance(user_profile.preferences, Preferences)
    assert user_profile.preferences.units == "metric"
    assert user_profile.preferences.show_tips is True


def test_user_profile_requires_sk_profile_literal(profile_kwargs):
    kwargs = {**profile_kwargs, "SK": "NOT_PROFILE"}

    with pytest.raises(ValidationError):
        UserProfile(**kwargs)


def test_user_profile_validates_email(profile_kwargs):
    kwargs = {**profile_kwargs, "email": "not-an-email"}

    with pytest.raises(ValidationError):
        UserProfile(**kwargs)


def test_to_ddb_item_serializes_datetimes_and_nests_preferences(user_profile):
    ddb_item = user_profile.to_ddb_item()

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
