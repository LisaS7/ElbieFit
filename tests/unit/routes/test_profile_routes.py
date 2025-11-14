import pytest

from app.routes import profile as profile_routes


@pytest.fixture(autouse=True)
def clear_dependency_overrides_after_each_test(client):
    # tests run here
    yield
    # cleanup after
    client.app.dependency_overrides.clear()


class FakeProfileRepo:
    def __init__(self, profile: dict | None, raise_error: bool = False):
        self._profile = profile
        self._raise_error = raise_error

    def get_for_user(self, user_sub: str) -> dict | None:
        if self._raise_error:
            raise RuntimeError("boom")
        return self._profile


def test_get_user_profile_success(authenticated_client):
    user_sub = "abc-123"

    repo = FakeProfileRepo(
        {
            "PK": f"USER#{user_sub}",
            "SK": "PROFILE",
            "display_name": "Lisa Test",
            "email": "lisa@example.com",
            "timezone": "Europe/London",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )

    authenticated_client.app.dependency_overrides[profile_routes.get_profile_repo] = (
        lambda: repo
    )

    response = authenticated_client.get("/profile/")

    assert response.status_code == 200
    assert "lisa@example.com" in response.text


def test_get_user_profile_not_found_shows_message(authenticated_client):

    class FakeProfileRepoNotFound:
        def get_for_user(self, user_sub: str):
            return None

    fake_repo = FakeProfileRepoNotFound()
    authenticated_client.app.dependency_overrides[profile_routes.get_profile_repo] = (
        lambda: fake_repo
    )

    response = authenticated_client.get("/profile/")

    assert response.status_code == 404
    assert "Profile not found" in response.text


def test_profile_db_error_returns_500(authenticated_client):

    class ExplodingProfileRepo:
        def get_for_user(self, user_sub: str) -> dict | None:
            raise RuntimeError("database is on fire")

    exploding_repo = ExplodingProfileRepo()
    authenticated_client.app.dependency_overrides[profile_routes.get_profile_repo] = (
        lambda: exploding_repo
    )

    response = authenticated_client.get("/profile/")

    assert response.status_code == 500
    text = response.text
    assert "Error 500" in text or "Something went wrong" in text
    assert "ElbieFit" in text
