from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit import RateLimitMiddleware
from app.settings import settings
from app.utils.db import RateLimitDdbError

# ─────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────


@pytest.fixture(autouse=True)
def enable_rate_limiting_for_middleware_tests():
    settings.RATE_LIMIT_ENABLED = True
    yield
    settings.RATE_LIMIT_ENABLED = False


@pytest.fixture
def test_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """
    Minimal app with RateLimitMiddleware installed.
    """
    monkeypatch.setattr(
        settings, "RATE_LIMIT_EXCLUDED_PREFIXES", ("/static", "/health", "/meta")
    )
    monkeypatch.setattr(settings, "RATE_LIMIT_READ_PER_MIN", 120)
    monkeypatch.setattr(settings, "RATE_LIMIT_WRITE_PER_MIN", 30)
    monkeypatch.setattr(settings, "DEMO_RATE_LIMIT_READ_PER_MIN", 60)
    monkeypatch.setattr(settings, "DEMO_RATE_LIMIT_WRITE_PER_MIN", 15)
    monkeypatch.setattr(settings, "RATE_LIMIT_TTL_SECONDS", 600)
    monkeypatch.setattr(settings, "DEMO_SESSION_COOKIE_NAME", "demo_session_id")

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.post("/ok")
    def ok_post():
        return {"ok": True}

    @app.get("/static/test")
    def static_test():
        return {"static": True}

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


@pytest.fixture
def rate_limit_allows(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """
    Default limiter behaviour: allow requests and record calls.
    """
    calls: list[dict] = []

    def fake_rate_limit_hit(*, client_id: str, limit: int, ttl_seconds: int):
        calls.append(
            {"client_id": client_id, "limit": limit, "ttl_seconds": ttl_seconds}
        )
        return (True, 0)

    monkeypatch.setattr("app.middleware.rate_limit.rate_limit_hit", fake_rate_limit_hit)
    return calls


@pytest.fixture
def rate_limit_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Limiter behaviour: block requests with a Retry-After value.
    """

    def fake_rate_limit_hit(*, client_id: str, limit: int, ttl_seconds: int):
        return (False, 17)

    monkeypatch.setattr("app.middleware.rate_limit.rate_limit_hit", fake_rate_limit_hit)


@pytest.fixture
def rate_limit_ddb_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Limiter behaviour: DynamoDB/storage error -> middleware should fail open.
    """

    def fake_rate_limit_hit(*, client_id: str, limit: int, ttl_seconds: int):
        raise RateLimitDdbError("ddb sad")

    monkeypatch.setattr("app.middleware.rate_limit.rate_limit_hit", fake_rate_limit_hit)


# ─────────────────────────────────────────
# Tests
# ─────────────────────────────────────────


def test_excluded_prefix_bypasses_rate_limit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def boom(*args, **kwargs):
        raise AssertionError(
            "rate_limit_hit should not be called for excluded prefixes"
        )

    monkeypatch.setattr("app.middleware.rate_limit.rate_limit_hit", boom)

    resp = client.get("/static/test")
    assert resp.status_code == 200
    assert resp.json() == {"static": True}


def test_get_uses_read_limit_for_real_users(
    client: TestClient, rate_limit_allows: list[dict]
):
    resp = client.get("/ok")
    assert resp.status_code == 200

    assert len(rate_limit_allows) == 1
    assert rate_limit_allows[0]["limit"] == settings.RATE_LIMIT_READ_PER_MIN
    assert rate_limit_allows[0]["ttl_seconds"] == settings.RATE_LIMIT_TTL_SECONDS
    assert rate_limit_allows[0]["client_id"].startswith("ip:")


def test_post_uses_write_limit_for_real_users(
    client: TestClient, rate_limit_allows: list[dict]
):
    resp = client.post("/ok")
    assert resp.status_code == 200

    assert len(rate_limit_allows) == 1
    assert rate_limit_allows[0]["limit"] == settings.RATE_LIMIT_WRITE_PER_MIN


def test_demo_cookie_uses_demo_limits(
    client: TestClient, rate_limit_allows: list[dict]
):
    client.cookies.set(settings.DEMO_SESSION_COOKIE_NAME, "demo-abc")

    # Demo GET -> demo read limit
    resp = client.get("/ok")
    assert resp.status_code == 200

    assert len(rate_limit_allows) == 1
    assert rate_limit_allows[0]["client_id"].startswith("demo:")
    assert rate_limit_allows[0]["limit"] == settings.DEMO_RATE_LIMIT_READ_PER_MIN

    rate_limit_allows.clear()

    # Demo POST -> demo write limit
    resp = client.post("/ok")
    assert resp.status_code == 200

    assert len(rate_limit_allows) == 1
    assert rate_limit_allows[0]["client_id"].startswith("demo:")
    assert rate_limit_allows[0]["limit"] == settings.DEMO_RATE_LIMIT_WRITE_PER_MIN


def test_rate_limited_request_returns_429_and_retry_after(
    client: TestClient, rate_limit_blocks: None
):
    resp = client.get("/ok")
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") == "17"
    assert "Rate limit exceeded" in resp.text


def test_rate_limit_ddb_error_fails_open(
    client: TestClient, rate_limit_ddb_error: None
):
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
