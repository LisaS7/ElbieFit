from app.routes import auth


def _patch_cognito_config(monkeypatch):
    """
    Make sure we don't depend on real env/settings for URL building.
    """
    monkeypatch.setattr(auth, "CLIENT_ID", "fake-client-id")
    monkeypatch.setattr(
        auth,
        "REDIRECT_URI",
        "https://example.com/auth/callback",
    )

    def fake_base_url() -> str:
        return "https://fake-domain.auth.eu-west-2.amazoncognito.com"

    monkeypatch.setattr(auth, "cognito_base_url", fake_base_url)


# --------------- Login ---------------


def test_auth_login_redirects_to_cognito(monkeypatch, client):
    _patch_cognito_config(monkeypatch)

    response = client.get("/auth/login", follow_redirects=False)

    assert response.status_code == 307  # default for RedirectResponse
    location = response.headers["location"]

    # Check the important bits of the URL
    assert location.startswith(
        "https://fake-domain.auth.eu-west-2.amazoncognito.com/oauth2/authorize"
    )
    assert "response_type=code" in location
    assert "client_id=fake-client-id" in location
    assert "redirect_uri=https://example.com/auth/callback" in location
    assert "scope=openid+email+profile" in location


# --------------- Callback ---------------
def test_auth_callback_missing_code_returns_400(monkeypatch, client):
    _patch_cognito_config(monkeypatch)

    # The `code` param is required, but `?code=` gives us an empty string,
    # which hits the `if not code` branch.
    response = client.get("/auth/callback?code=", follow_redirects=False)
    body = response.text

    assert response.status_code == 400
    assert "Error 400" in body
    assert "ElbieFit" in body


def test_auth_callback_token_exchange_failure(monkeypatch, dummy_response, client):
    _patch_cognito_config(monkeypatch)

    def fake_post(*args, **kwargs):
        return dummy_response(
            status_code=400,
            text="something exploded",
        )

    # Patch the module's requests, not the global library
    monkeypatch.setattr(auth.requests, "post", fake_post)

    response = client.get("/auth/callback?code=abc123", follow_redirects=False)
    body = response.text

    assert response.status_code == 400
    assert "Error 400" in body
    assert "ElbieFit" in body


def test_auth_callback_invalid_token_type(monkeypatch, dummy_response, client):
    _patch_cognito_config(monkeypatch)

    def fake_post(*args, **kwargs):
        return dummy_response(
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
    body = response.text

    assert response.status_code == 400
    assert "Error 400" in body
    assert "ElbieFit" in body


def test_auth_callback_success_sets_cookies_and_redirects(
    monkeypatch, dummy_response, client
):
    _patch_cognito_config(monkeypatch)

    def fake_post(*args, **kwargs):
        return dummy_response(
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
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "id_token=id123" in set_cookie_header
    assert "access_token=access123" in set_cookie_header
    assert "refresh_token=refresh123" in set_cookie_header

    # Sanity check on max_age for id/access tokens
    assert "Max-Age=3600" in set_cookie_header


# --------------- Logout ---------------


def test_logout_clears_cookies_and_redirects(monkeypatch, client):
    _patch_cognito_config(monkeypatch)

    response = client.get("/auth/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # delete_cookie writes cookies with Max-Age=0
    set_cookie_header = response.headers.get("set-cookie", "")
    # We don't care about exact format, just that they are being cleared
    assert "id_token=" in set_cookie_header
    assert "access_token=" in set_cookie_header
    assert "refresh_token=" in set_cookie_header
    assert "Max-Age=0" in set_cookie_header
