from datetime import datetime, timezone

import pytest
from test_data import USER_EMAIL, USER_PK

from app.models.profile import UserProfile
from app.routes import profile as profile_routes


@pytest.fixture(autouse=True)
def clear_dependency_overrides_after_each_test(client):
    # tests run here
    yield
    # cleanup after
    client.app.dependency_overrides.clear()


class FakeProfileRepo:
    def __init__(self, profile: UserProfile | None, raise_error: bool = False):
        self._profile = profile
        self._raise_error = raise_error

    def get_for_user(self, user_sub: str) -> UserProfile | None:
        if self._raise_error:
            raise RuntimeError("boom")
        return self._profile


def test_get_user_profile_success(authenticated_client):
    profile = UserProfile(
        PK=USER_PK,
        SK="PROFILE",
        display_name="Lisa Test",
        email=USER_EMAIL,
        timezone="Europe/London",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        # preferences omitted -> defaults are fine
    )

    repo = FakeProfileRepo(profile)

    authenticated_client.app.dependency_overrides[profile_routes.get_profile_repo] = (
        lambda: repo
    )

    response = authenticated_client.get("/profile/")

    assert response.status_code == 200
    assert USER_EMAIL in response.text
    assert "Lisa Test" in response.text
    assert "Europe/London" in response.text


def test_get_user_profile_not_found_shows_message(authenticated_client):
    repo = FakeProfileRepo(profile=None)

    authenticated_client.app.dependency_overrides[profile_routes.get_profile_repo] = (
        lambda: repo
    )

    response = authenticated_client.get("/profile/")

    assert response.status_code == 404
    assert "Profile not found" in response.text


def test_profile_db_error_returns_500(authenticated_client):
    repo = FakeProfileRepo(profile=None, raise_error=True)

    authenticated_client.app.dependency_overrides[profile_routes.get_profile_repo] = (
        lambda: repo
    )

    response = authenticated_client.get("/profile/")

    assert response.status_code == 500
    text = response.text
    assert "Error 500" in text or "Something went wrong" in text
    assert "ElbieFit" in text
