from urllib.parse import parse_qs, urlparse

from app.routes import auth

# ─────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ─────────────────────────────────────────────────────────────


class FakeSettings:
    PROJECT_NAME = "elbiefit"
    REGION = "eu-west-2"
    ENV = "test"
    COGNITO_AUDIENCE = "fake-aud"
    COGNITO_DOMAIN = "fake-domain"
    COGNITO_REDIRECT_URI = "https://example.com/auth/callback"
    COGNITO_ISSUER_URL = (
        "https://cognito-idp.eu-west-2.amazonaws.com/eu-west-2_fakepool"
    )

    def cognito_base_url(self) -> str:
        return f"https://{self.COGNITO_DOMAIN}.auth.{self.REGION}.amazoncognito.com"

    def auth_url(self) -> str:
        return f"{self.cognito_base_url()}/oauth2/authorize"

    def token_url(self) -> str:
        return f"{self.cognito_base_url()}/oauth2/token"


def patch_auth_settings(monkeypatch) -> FakeSettings:
    """
    Keep auth route URL-building deterministic.
    Returns the fake settings so tests can assert against it.
    """
    fake_settings = FakeSettings()
    monkeypatch.setattr(auth, "settings", fake_settings)
    monkeypatch.setattr(auth, "CLIENT_ID", fake_settings.COGNITO_AUDIENCE)
    monkeypatch.setattr(auth, "REDIRECT_URI", fake_settings.COGNITO_REDIRECT_URI)
    return fake_settings


def assert_error_page(response, status_code: int) -> None:
    assert response.status_code == status_code
    body = response.text
    assert f"Error {status_code}" in body
    assert "ElbieFit" in body


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────

# ───────────────────────── /auth/login ─────────────────────────


def test_auth_login_redirects_to_cognito(monkeypatch, client):
    settings = patch_auth_settings(monkeypatch)

    response = client.get("/auth/login", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers["location"]

    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == settings.auth_url()

    qs = parse_qs(parsed.query)
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == [settings.COGNITO_AUDIENCE]
    assert qs["redirect_uri"] == [settings.COGNITO_REDIRECT_URI]
    assert qs["scope"] == ["openid email profile"]


# ───────────────────────── /auth/callback ─────────────────────────


def test_auth_callback_missing_code_returns_400(monkeypatch, client):
    patch_auth_settings(monkeypatch)

    response = client.get("/auth/callback?code=", follow_redirects=False)

    assert_error_page(response, 400)


def test_auth_callback_token_exchange_failure(monkeypatch, fake_response, client):
    patch_auth_settings(monkeypatch)

    def fake_post(*args, **kwargs):
        return fake_response(status_code=400, text="something exploded")

    # Patch the module's requests, not the global library
    monkeypatch.setattr(auth.requests, "post", fake_post)

    response = client.get("/auth/callback?code=abc123", follow_redirects=False)

    assert_error_page(response, 400)


def test_auth_callback_invalid_token_type(monkeypatch, fake_response, client):
    patch_auth_settings(monkeypatch)

    def fake_post(*args, **kwargs):
        return fake_response(
            status_code=200,
            json_data={
                "token_type": "NotBearer",
                "id_token": "id123",
                "access_token": "access123",
                "refresh_token": "refresh123",
                "expires_in": 3600,
            },
        )

    monkeypatch.setattr(auth.requests, "post", fake_post)

    response = client.get("/auth/callback?code=abc123", follow_redirects=False)

    assert_error_page(response, 400)


def test_auth_callback_success_sets_cookies_and_redirects(
    monkeypatch, fake_response, client
):
    patch_auth_settings(monkeypatch)

    def fake_post(*args, **kwargs):
        return fake_response(
            status_code=200,
            json_data={
                "token_type": "Bearer",
                "id_token": "id123",
                "access_token": "access123",
                "refresh_token": "refresh123",
                "expires_in": 3600,
            },
        )

    monkeypatch.setattr(auth.requests, "post", fake_post)

    response = client.get("/auth/callback?code=abc123", follow_redirects=False)

    # Redirect to home
    assert response.status_code == 302
    assert response.headers["location"] == "/"

    # Cookies are set – Test Client merges multiple Set-Cookie headers into one string
    set_cookie = response.headers.get("set-cookie", "")
    assert "id_token=id123" in set_cookie
    assert "access_token=access123" in set_cookie
    assert "refresh_token=refresh123" in set_cookie
    assert "Max-Age=3600" in set_cookie


# --------------- Logout ---------------


def test_logout_clears_cookies_and_redirects(monkeypatch, client):
    patch_auth_settings(monkeypatch)

    response = client.get("/auth/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"

    set_cookie = response.headers.get("set-cookie", "")
    assert "id_token=" in set_cookie
    assert "access_token=" in set_cookie
    assert "refresh_token=" in set_cookie
    assert "Max-Age=0" in set_cookie
