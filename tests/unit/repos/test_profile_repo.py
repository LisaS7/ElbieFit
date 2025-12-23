import pytest

from app.models.profile import UserProfile
from app.repositories.errors import ProfileRepoError
from app.repositories.profile import DynamoProfileRepository
from tests.test_data import USER_EMAIL, USER_PK, USER_SUB


def test_get_for_user_success(fake_table):
    expected_item = {
        "PK": USER_PK,
        "SK": "PROFILE",
        "display_name": "Lisa Test",
        "email": USER_EMAIL,
        "timezone": "Europe/London",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-02T12:00:00Z",
    }

    fake_table.response = {
        "Item": expected_item,
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    repo = DynamoProfileRepository(table=fake_table)

    profile = repo.get_for_user(USER_SUB)

    assert isinstance(profile, UserProfile)
    assert profile.PK == USER_PK
    assert profile.SK == "PROFILE"
    assert profile.display_name == "Lisa Test"
    assert str(profile.email) == USER_EMAIL
    assert profile.timezone == "Europe/London"
    assert profile.preferences.default_view == "workouts"  # default sanity check

    assert fake_table.last_get_kwargs == {
        "Key": {"PK": USER_PK, "SK": "PROFILE"},
        "ConsistentRead": True,
    }


def test_get_for_user_not_found_returns_none(fake_table):
    fake_table.response = {"ResponseMetadata": {"RequestId": "req-123"}}

    repo = DynamoProfileRepository(table=fake_table)

    result = repo.get_for_user(USER_SUB)

    assert result is None


def test_get_for_user_wraps_repo_error(failing_get_table):
    repo = DynamoProfileRepository(table=failing_get_table)

    with pytest.raises(ProfileRepoError):
        repo.get_for_user(USER_SUB)


def test_get_for_user_invalid_item_raises_profile_repo_error(fake_table):
    bad_item = {
        "PK": USER_PK,
        "SK": "PROFILE",
        "display_name": "Lisa Test",
        "email": USER_EMAIL,
        "timezone": "Mars/Phobos",  # invalid -> triggers model validation failure
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-02T12:00:00Z",
    }

    fake_table.response = {
        "Item": bad_item,
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    repo = DynamoProfileRepository(table=fake_table)

    with pytest.raises(ProfileRepoError) as exc:
        repo.get_for_user(USER_SUB)

    assert "Failed to create profile model from item" in str(exc.value)
