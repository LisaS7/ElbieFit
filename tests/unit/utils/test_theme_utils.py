import pytest
from fastapi import Response

from app.utils import theme as theme_utils
from tests.test_data import USER_SUB


class FakePreferences:
    def __init__(self, theme: str | None):
        self.theme = theme


class FakeProfile:
    def __init__(self, theme: str | None):
        self.preferences = FakePreferences(theme)


class FakeRepo:
    def __init__(
        self, profile: FakeProfile | None = None, raises: Exception | None = None
    ):
        self._profile = profile
        self._raises = raises

    def get_for_user(self, sub: str):
        assert sub == USER_SUB
        if self._raises:
            raise self._raises
        return self._profile


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────


def _set_cookie_headers(resp: Response) -> list[str]:
    headers: list[str] = []
    for k, v in resp.raw_headers:
        if k.lower() == b"set-cookie":
            headers.append(v.decode("latin-1"))
    return headers


def _has_theme_cookie(resp: Response, expected_theme: str) -> bool:
    prefix = f"theme={expected_theme}"
    return any(h.startswith(prefix) for h in _set_cookie_headers(resp))


@pytest.fixture()
def response() -> Response:
    return Response()


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    # Keep this stable for all tests in this file.
    monkeypatch.setattr(
        theme_utils.settings, "COGNITO_ISSUER_URL", "https://issuer.example"
    )
    monkeypatch.setattr(theme_utils.settings, "COGNITO_AUDIENCE", "fake-audience")
    monkeypatch.setattr(theme_utils.settings, "THEMES", {"prehistoric", "ink"})


@pytest.fixture()
def stub_decode_and_urls(monkeypatch):
    # Prevent any real JWT/JWKS behaviour and keep the tests pure.
    monkeypatch.setattr(
        theme_utils, "get_jwks_url", lambda issuer_url: "https://jwks.example"
    )
    monkeypatch.setattr(
        theme_utils,
        "decode_and_validate_id_token",
        lambda **kwargs: {"sub": USER_SUB},
    )


# ─────────────────────────────────────────
# set_theme_cookie
# ─────────────────────────────────────────


def test_set_theme_cookie_sets_cookie(response: Response):
    theme_utils.set_theme_cookie(response, "ink")

    assert _has_theme_cookie(response, "ink") is True


# ─────────────────────────────────────────
# get_theme_cookie_from_profile
# ─────────────────────────────────────────


def test_get_theme_cookie_from_profile_happy_path_sets_cookie(
    monkeypatch, response: Response, stub_decode_and_urls
):
    monkeypatch.setattr(
        theme_utils,
        "DynamoProfileRepository",
        lambda: FakeRepo(profile=FakeProfile(theme="ink")),
    )

    theme_utils.get_theme_cookie_from_profile(response, id_token="header.payload.sig")

    assert _has_theme_cookie(response, "ink") is True


def test_get_theme_cookie_from_profile_no_sub_does_nothing(
    monkeypatch, response: Response
):
    monkeypatch.setattr(
        theme_utils, "get_jwks_url", lambda issuer_url: "https://jwks.example"
    )
    monkeypatch.setattr(
        theme_utils,
        "decode_and_validate_id_token",
        lambda **kwargs: {},  # no sub
    )
    monkeypatch.setattr(
        theme_utils,
        "DynamoProfileRepository",
        lambda: FakeRepo(profile=FakeProfile(theme="ink")),
    )

    theme_utils.get_theme_cookie_from_profile(response, id_token="header.payload.sig")

    assert _set_cookie_headers(response) == []


def test_get_theme_cookie_from_profile_repo_error_does_nothing(
    monkeypatch, response: Response, stub_decode_and_urls
):
    monkeypatch.setattr(
        theme_utils,
        "DynamoProfileRepository",
        lambda: FakeRepo(raises=RuntimeError("boom")),
    )

    theme_utils.get_theme_cookie_from_profile(response, id_token="header.payload.sig")

    assert _set_cookie_headers(response) == []


def test_get_theme_cookie_from_profile_missing_theme_does_nothing(
    monkeypatch, response: Response, stub_decode_and_urls
):
    monkeypatch.setattr(
        theme_utils,
        "DynamoProfileRepository",
        lambda: FakeRepo(profile=FakeProfile(theme=None)),
    )

    theme_utils.get_theme_cookie_from_profile(response, id_token="header.payload.sig")

    assert _set_cookie_headers(response) == []


def test_get_theme_cookie_from_profile_invalid_theme_does_nothing(
    monkeypatch, response: Response, stub_decode_and_urls
):
    monkeypatch.setattr(
        theme_utils,
        "DynamoProfileRepository",
        lambda: FakeRepo(profile=FakeProfile(theme="banana")),
    )

    theme_utils.get_theme_cookie_from_profile(response, id_token="header.payload.sig")

    assert _set_cookie_headers(response) == []
