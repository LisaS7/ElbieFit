from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.routes import demo as demo_routes
from app.settings import settings
from app.utils import auth as auth_utils
from tests.test_data import USER_SUB

# ─────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────


@pytest.fixture
def client_with_sub(app_instance):
    """
    Factory: returns a TestClient with require_auth overridden
    to return a claims dict containing the requested sub.
    """

    def _make(sub: str) -> TestClient:
        def fake_require_auth():
            return {"sub": sub}

        app_instance.dependency_overrides[auth_utils.require_auth] = fake_require_auth
        client = TestClient(app_instance, raise_server_exceptions=False)

        def _finalize():
            app_instance.dependency_overrides.pop(auth_utils.require_auth, None)
            client.close()

        client._elbiefit_finalize = _finalize  # type: ignore[attr-defined]
        return client

    return _make


@pytest.fixture
def demo_settings(monkeypatch):
    """
    Helper fixture to set demo settings for the duration of a test.
    """
    monkeypatch.setattr(settings, "DEMO_USER_SUB", USER_SUB, raising=False)
    monkeypatch.setattr(settings, "DEMO_RESET_COOLDOWN_SECONDS", 300, raising=False)


@pytest.fixture
def demo_actions(monkeypatch):
    """
    Patch enforce_cooldown/reset_user in the *routes module* and capture calls.
    """
    calls = []

    def fake_enforce_cooldown(user_sub: str, cooldown_seconds: int):
        calls.append(("enforce_cooldown", user_sub, cooldown_seconds))

    def fake_reset_user(user_sub: str):
        calls.append(("reset_user", user_sub))

    monkeypatch.setattr(demo_routes, "enforce_cooldown", fake_enforce_cooldown)
    monkeypatch.setattr(demo_routes, "reset_user", fake_reset_user)

    return calls


# ─────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────


def test_reset_demo_returns_404_if_no_demo_sub(client_with_sub, monkeypatch):
    client = client_with_sub(USER_SUB)
    try:
        monkeypatch.setattr(settings, "DEMO_USER_SUB", None, raising=False)

        resp = client.post("/demo/reset")
        assert resp.status_code == 404
    finally:
        client._elbiefit_finalize()  # type: ignore[attr-defined]


def test_reset_demo_returns_403_for_non_demo_user(
    client_with_sub, demo_settings, monkeypatch
):
    client = client_with_sub("not-the-demo-user")
    try:
        monkeypatch.setattr(settings, "DEMO_USER_SUB", USER_SUB, raising=False)

        resp = client.post("/demo/reset")
        assert resp.status_code == 403
    finally:
        client._elbiefit_finalize()  # type: ignore[attr-defined]


def test_reset_demo_happy_path_calls_cooldown_then_reset_and_returns_204(
    client_with_sub, demo_settings, demo_actions, monkeypatch
):
    client = client_with_sub(USER_SUB)
    try:
        monkeypatch.setattr(settings, "DEMO_USER_SUB", USER_SUB, raising=False)
        monkeypatch.setattr(settings, "DEMO_RESET_COOLDOWN_SECONDS", 123, raising=False)

        resp = client.post("/demo/reset")
        assert resp.status_code == 204
        assert resp.text == ""  # 204 means no body

        assert demo_actions == [
            ("enforce_cooldown", USER_SUB, 123),
            ("reset_user", USER_SUB),
        ]
    finally:
        client._elbiefit_finalize()  # type: ignore[attr-defined]


def test_reset_demo_bubbles_up_429_from_enforce_cooldown(
    client_with_sub, demo_settings, monkeypatch
):
    client = client_with_sub(USER_SUB)
    try:
        monkeypatch.setattr(settings, "DEMO_USER_SUB", USER_SUB, raising=False)

        def fake_enforce_cooldown(user_sub: str, cooldown_seconds: int):
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="nope")

        monkeypatch.setattr(demo_routes, "enforce_cooldown", fake_enforce_cooldown)

        # if enforce_cooldown fails, reset_user must not be called
        reset_called = {"called": False}

        def fake_reset_user(user_sub: str):
            reset_called["called"] = True

        monkeypatch.setattr(demo_routes, "reset_user", fake_reset_user)

        resp = client.post("/demo/reset")
        assert resp.status_code == 429
        assert reset_called["called"] is False
    finally:
        client._elbiefit_finalize()  # type: ignore[attr-defined]


def test_reset_demo_bubbles_up_500_from_reset_user(
    client_with_sub, demo_settings, monkeypatch
):
    client = client_with_sub(USER_SUB)
    try:
        monkeypatch.setattr(settings, "DEMO_USER_SUB", USER_SUB, raising=False)

        # cooldown ok
        monkeypatch.setattr(
            demo_routes, "enforce_cooldown", lambda *_args, **_kwargs: None
        )

        def fake_reset_user(user_sub: str):
            from fastapi import HTTPException

            raise HTTPException(status_code=500, detail="boom")

        monkeypatch.setattr(demo_routes, "reset_user", fake_reset_user)

        resp = client.post("/demo/reset")
        assert resp.status_code == 500
    finally:
        client._elbiefit_finalize()  # type: ignore[attr-defined]
