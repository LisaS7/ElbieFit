import pytest
from fastapi import Request

from app.utils import auth as auth_utils


class DummyRequest:
    def __init__(self, cookies):
        self.cookies = cookies


@pytest.fixture
def make_request_with_cookies():
    """
    Fixture returning a function that builds a FastAPI Request with given cookies.
    Example:
        request = make_request_with_cookies({"id_token": "abc"})
    """

    def _build(cookies: dict) -> Request:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()
        scope = {
            "type": "http",
            "headers": [(b"cookie", cookie_header)],
        }
        return Request(scope)

    return _build


@pytest.fixture
def dummy_request():
    def _make(cookies):
        return DummyRequest(cookies)

    return _make


@pytest.fixture
def stub_basic_auth_helpers(monkeypatch):
    def fake_get_id_token(request):
        return "fake-token"

    def fake_get_jwks_url(region, issuer):
        return "https://example.com/jwks.json"

    monkeypatch.setattr(auth_utils, "get_id_token", fake_get_id_token)
    monkeypatch.setattr(auth_utils, "get_jwks_url", fake_get_jwks_url)
