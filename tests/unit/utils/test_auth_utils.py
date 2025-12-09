import pytest
from fastapi import HTTPException

from app.utils import auth

# The functions under test expect a FastAPI `Request` object, but for unit tests
# we only need something that provides a `.cookies` attribute. To avoid pulling
# in the whole FastAPI request machinery, we use a lightweight DummyRequest.
# This triggers type checker complaints because DummyRequest is not a real
# `Request`, so we silence those specific errors with `type: ignore[arg-type]`.
# Runtime behaviour is unaffected; the tested code only accesses `.cookies`.


# Switch off the auth override for this module
@pytest.fixture(autouse=True)
def _force_real_auth_flow(monkeypatch):
    """
    For this module, always disable the local-dev auth bypass so tests
    exercise the real token validation logic by default.
    """
    monkeypatch.setattr(auth.settings, "DISABLE_AUTH_FOR_LOCAL_DEV", False)


# ------------ Get jwks url ------------


def test_get_jwks_url_success():
    issuer = "fake_issuer"
    result = auth.get_jwks_url("eu-west-2", issuer)
    assert (
        result
        == f"https://cognito-idp.eu-west-2.amazonaws.com/{issuer}/.well-known/jwks.json"
    )


def test_get_jwks_url_missing_params():
    # missing region
    with pytest.raises(HTTPException) as err:
        auth.get_jwks_url("", "issuer")

    assert err.value.status_code == 500

    # missing issuer
    with pytest.raises(HTTPException) as err2:
        auth.get_jwks_url("eu-west-2", "")

    assert err2.value.status_code == 500


# ------------ Get ID Token ------------


def test_get_id_token_success(dummy_request):
    req = dummy_request(cookies={"id_token": "test-token"})
    result = auth.get_id_token(req)  # type: ignore[arg-type]
    assert result == "test-token"


def test_get_id_token_missing(dummy_request):
    req = dummy_request(cookies={})

    with pytest.raises(HTTPException) as err:
        auth.get_id_token(req)  # type: ignore[arg-type]

    assert err.value.status_code == 401
    assert "ID token is missing" in err.value.detail


# ------------ Decode and validate token ------------


fake_jwks_url = "https://example.com/.well-known/jwks.json"
fake_token = "header.payload.sig"


class DummyKey:
    key = "dummy-public-key"


class DummyJwksClient:
    def __init__(self, url):
        self.url = url

    def get_signing_key_from_jwt(self, token):
        assert token == fake_token
        return DummyKey()


def test_decode_and_validate_token_success(monkeypatch):

    def dummy_decode(token, signing_key, algorithms, issuer, audience):
        assert token == fake_token
        assert signing_key == "dummy-public-key"
        assert algorithms == ["RS256"]
        return {
            "sub": "user-123",
            "exp": 1700000000,
            "token_use": "id",
        }

    # patch PyJWKClient used in auth module
    monkeypatch.setattr(auth, "PyJWKClient", DummyJwksClient)
    # patch jwt.decode in auth module
    monkeypatch.setattr(auth.jwt, "decode", dummy_decode)

    decoded = auth.decode_and_validate_id_token(
        id_token=fake_token,
        jwks_url=fake_jwks_url,
        issuer=auth.ISSUER,
        audience=auth.AUDIENCE,
    )

    assert decoded["sub"] == "user-123"
    assert decoded["token_use"] == "id"
    assert "exp" in decoded


def test_decode_and_validate_id_token_wrong_token_use(monkeypatch):

    def dummy_decode(token, signing_key, algorithms, issuer, audience):
        return {
            "sub": "user-123",
            "exp": 1700000000,
            "token_use": "access",
        }

    monkeypatch.setattr(auth, "PyJWKClient", DummyJwksClient)
    monkeypatch.setattr(auth.jwt, "decode", dummy_decode)

    with pytest.raises(HTTPException) as err:
        auth.decode_and_validate_id_token(
            id_token=fake_token,
            jwks_url=fake_jwks_url,
            issuer=auth.ISSUER,
            audience=auth.AUDIENCE,
        )

    assert err.value.status_code == 401
    assert "Wrong token type" in err.value.detail


# ------------ Require auth ------------


@pytest.mark.asyncio
async def test_require_auth_success(monkeypatch, dummy_request):
    req = dummy_request(cookies={"id_token": "fake-token"})

    # track what gets called
    called = {}

    def fake_get_id_token(request):
        called["get_id_token"] = True
        return "fake-token"

    def fake_get_jwks_url(region, issuer):
        called["get_jwks_url"] = True
        return "https://example.com/jwks.json"

    def fake_decode_and_validate(id_token, jwks_url, issuer, audience):
        called["decode_and_validate"] = True
        return {"sub": "user-123", "exp": 1700000000, "token_use": "id"}

    def fake_log_sub_and_exp(decoded):
        called["log_sub_and_exp"] = decoded

    # monkeypatch helpers inside auth module
    monkeypatch.setattr(auth, "get_id_token", fake_get_id_token)
    monkeypatch.setattr(auth, "get_jwks_url", fake_get_jwks_url)
    monkeypatch.setattr(auth, "decode_and_validate_id_token", fake_decode_and_validate)
    monkeypatch.setattr(auth, "log_sub_and_exp", fake_log_sub_and_exp)

    decoded = await auth.require_auth(req)  # type: ignore[arg-type]

    assert decoded["sub"] == "user-123"
    assert called["get_id_token"]
    assert called["get_jwks_url"]
    assert called["decode_and_validate"]
    assert called["log_sub_and_exp"]["sub"] == "user-123"


@pytest.mark.asyncio
async def test_require_auth_expired_token(
    monkeypatch, dummy_request, stub_basic_auth_helpers
):
    req = dummy_request(cookies={"id_token": "fake-token"})

    def fake_decode_and_validate(id_token, jwks_url, issuer, audience):
        # simulate jwt expired
        raise auth.jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(auth, "decode_and_validate_id_token", fake_decode_and_validate)

    with pytest.raises(HTTPException) as err:
        await auth.require_auth(req)  # type: ignore[arg-type]

    assert err.value.status_code == 401
    assert "Token expired" in err.value.detail


@pytest.mark.asyncio
async def test_require_auth_invalid_token(
    monkeypatch, dummy_request, stub_basic_auth_helpers
):
    req = dummy_request(cookies={"id_token": "fake-token"})

    def fake_decode_and_validate(id_token, jwks_url, issuer, audience):
        raise auth.InvalidTokenError("bad token")

    monkeypatch.setattr(auth, "decode_and_validate_id_token", fake_decode_and_validate)

    with pytest.raises(HTTPException) as err:
        await auth.require_auth(req)  # type: ignore[arg-type]

    assert err.value.status_code == 401
    assert "Invalid token" in err.value.detail


@pytest.mark.asyncio
async def test_require_auth_generic_error(
    monkeypatch, dummy_request, stub_basic_auth_helpers
):
    req = dummy_request(cookies={"id_token": "fake-token"})

    def fake_decode_and_validate(id_token, jwks_url, issuer, audience):
        raise RuntimeError("something unexpected")

    monkeypatch.setattr(auth, "decode_and_validate_id_token", fake_decode_and_validate)

    with pytest.raises(HTTPException) as err:
        await auth.require_auth(req)  # type: ignore[arg-type]

    assert err.value.status_code == 401
    assert "Invalid token" in err.value.detail
