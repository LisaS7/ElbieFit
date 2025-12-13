from typing import Any

import pytest

from app.utils import auth as auth_utils
from tests.test_data import USER_SUB


@pytest.fixture
def stub_basic_auth_helpers(monkeypatch):
    def fake_get_id_token(request):
        return "fake-token"

    def fake_get_jwks_url(region, issuer):
        return "https://example.com/jwks.json"

    monkeypatch.setattr(auth_utils, "get_id_token", fake_get_id_token)
    monkeypatch.setattr(auth_utils, "get_jwks_url", fake_get_jwks_url)


@pytest.fixture
def auth_pipeline(monkeypatch):
    """
    Patch the auth pipeline helpers and capture calls.
    Returns a dict with 'calls' and allows overriding return values.
    """
    calls: dict[str, Any] = {}

    def fake_get_id_token(request):
        calls["get_id_token"] = True
        return "fake-token"

    def fake_get_jwks_url(region, issuer):
        calls["get_jwks_url"] = (region, issuer)
        return "https://example.com/jwks.json"

    def fake_decode_and_validate(id_token, jwks_url, issuer, audience):
        calls["decode_and_validate"] = (id_token, jwks_url, issuer, audience)
        return {"sub": USER_SUB, "exp": 1700000000, "token_use": "id"}

    def fake_log_sub_and_exp(decoded):
        calls["log_sub_and_exp"] = decoded

    monkeypatch.setattr(auth_utils, "get_id_token", fake_get_id_token)
    monkeypatch.setattr(auth_utils, "get_jwks_url", fake_get_jwks_url)
    monkeypatch.setattr(
        auth_utils, "decode_and_validate_id_token", fake_decode_and_validate
    )
    monkeypatch.setattr(auth_utils, "log_sub_and_exp", fake_log_sub_and_exp)

    return calls
