from app.utils import db


def test_profile_success_renders_template_with_formatted_date(
    monkeypatch, authenticated_client
):
    # Fake profile data
    profile_from_db = {
        "display_name": "Lisa Test",
        "email": "lisa@example.com",
        "created_at": "2025-11-13T12:00:00Z",
        "units": "metric",
        "timezone": "Europe/London",
    }

    def fake_get_user_profile(user_sub: str):
        assert user_sub == "test-user-sub"
        return profile_from_db

    monkeypatch.setattr(db, "get_user_profile", fake_get_user_profile)

    response = authenticated_client.get("/profile/")

    assert response.status_code == 200
    # TemplateResponse sets these attributes in tests
    context = getattr(response, "context")
    assert context["user_sub"] == "test-user-sub"
    assert context["profile"]["display_name"] == "Lisa Test"

    # Our route should have added a human-readable date
    assert context["profile"]["created_at_readable"] == "13 November 2025"

    # And the rendered HTML should contain it too
    text = response.text
    assert "Lisa Test" in text
    assert "13 November 2025" in text


def test_profile_not_found_returns_404_template(monkeypatch, authenticated_client):
    def fake_get_user_profile(user_sub: str):
        return None

    monkeypatch.setattr(db, "get_user_profile", fake_get_user_profile)

    response = authenticated_client.get("/profile/")

    assert response.status_code == 404
    assert getattr(response, "template") is not None
    context = getattr(response, "context")

    assert context["profile"] is None
    assert context["user_sub"] == "test-user-sub"


def test_profile_db_error_returns_500(monkeypatch, authenticated_client):
    def fake_get_user_profile(user_sub: str):
        raise RuntimeError("database is on fire")

    monkeypatch.setattr(db, "get_user_profile", fake_get_user_profile)

    response = authenticated_client.get("/profile/")

    assert response.status_code == 500
    text = response.text
    assert "Error 500" in text or "Something went wrong" in text
    assert "ElbieFit" in text
