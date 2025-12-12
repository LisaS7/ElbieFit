from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app
from app.models.workout import Workout, WorkoutSet
from app.utils import auth as auth_utils
from app.utils import dates, db
from tests.test_data import TEST_DATE_2, TEST_WORKOUT_ID_2, USER_SUB


@pytest.fixture
def fixed_now(monkeypatch) -> datetime:
    now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(dates, "now", lambda: now)
    return now


# --------------- Request ---------------


class FakeRequest:
    def __init__(self, cookies):
        self.cookies = cookies


@pytest.fixture
def fake_request():
    def _make(cookies):
        return FakeRequest(cookies)

    return _make


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
def stub_basic_auth_helpers(monkeypatch):
    def fake_get_id_token(request):
        return "fake-token"

    def fake_get_jwks_url(region, issuer):
        return "https://example.com/jwks.json"

    monkeypatch.setattr(auth_utils, "get_id_token", fake_get_id_token)
    monkeypatch.setattr(auth_utils, "get_jwks_url", fake_get_jwks_url)


# --------------- Response ---------------


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


@pytest.fixture
def fake_response():
    """
    Factory fixture that returns a function to build FakeResponse objects.
    Example:
        resp = fake_response(status_code=400, text="boom")
    """

    def _make(status_code=200, json_data=None, text=""):
        return FakeResponse(status_code=status_code, json_data=json_data, text=text)

    return _make


# --------------- Test Clients ---------------


@pytest.fixture(scope="session")
def app_instance():
    return app


@pytest.fixture
def client(app_instance):
    """Plain client, real dependencies."""
    return TestClient(app_instance, raise_server_exceptions=False)


@pytest.fixture
def authenticated_client(app_instance):
    """
    Client with auth.require_auth overridden to always
    return a fake, valid claims dict.
    """

    def fake_require_auth(request: Request):
        return {"sub": "test-user-sub"}

    app_instance.dependency_overrides[auth_utils.require_auth] = fake_require_auth
    client = TestClient(app_instance, raise_server_exceptions=False)

    try:
        yield client
    finally:
        # Clean up so other tests see the real dependency
        app_instance.dependency_overrides.pop(auth_utils.require_auth, None)


# --------------- Item Factories ---------------


@pytest.fixture
def workout_factory(fixed_now) -> Callable[..., Workout]:
    def _make(**overrides: Any) -> Workout:
        base = Workout(
            PK=db.build_user_pk(USER_SUB),
            SK=db.build_workout_sk(TEST_DATE_2, TEST_WORKOUT_ID_2),
            type="workout",
            date=TEST_DATE_2,
            name="Move Me Dino Day",
            tags=["upper"],
            notes="Roar",
            created_at=fixed_now,
            updated_at=fixed_now,
        )
        return base.model_copy(update=overrides)

    return _make


@pytest.fixture
def set_factory(fixed_now) -> Callable[..., WorkoutSet]:
    def _make(**overrides: Any) -> WorkoutSet:
        base = WorkoutSet(
            PK=db.build_user_pk(USER_SUB),
            SK=db.build_set_sk(TEST_DATE_2, TEST_WORKOUT_ID_2, 1),
            type="set",
            exercise_id="squat",
            set_number=1,
            reps=8,
            weight_kg=Decimal("60"),
            rpe=7,
            created_at=fixed_now,
            updated_at=fixed_now,
        )
        return base.model_copy(update=overrides)

    return _make
