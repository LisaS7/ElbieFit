from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.exercise import Exercise
from app.models.profile import UserProfile
from app.models.workout import Workout, WorkoutSet

# ───────────── Exercise  ─────────────


@pytest.fixture
def exercise_kwargs() -> dict:
    return {
        "PK": "EXERCISE#PUSHUP",
        "SK": "EXERCISE#PUSHUP",
        "type": "exercise",
        "name": "Push-up",
        "muscles": ["chest", "triceps"],
        "equipment": "bodyweight",
        "category": "strength",
        "created_at": datetime(2025, 1, 1, 12, 0, 0),
        "updated_at": datetime(2025, 1, 2, 12, 0, 0),
    }


@pytest.fixture
def make_exercise(exercise_kwargs):

    def _make(**overrides) -> Exercise:
        data = {**exercise_kwargs, **overrides}
        return Exercise(**data)

    return _make


@pytest.fixture
def example_exercise(make_exercise) -> Exercise:
    return make_exercise()


# ───────────── Profile  ─────────────
@pytest.fixture
def profile_kwargs() -> dict:
    return {
        "PK": "USER#123",
        "SK": "PROFILE",
        "display_name": "Lisa Test",
        "email": "lisa@example.com",
        "created_at": datetime(2025, 1, 1, 12, 0, 0),
        "updated_at": datetime(2025, 1, 1, 13, 0, 0),
        "timezone": "Europe/London",
    }


@pytest.fixture
def user_profile(profile_kwargs) -> UserProfile:
    return UserProfile(**profile_kwargs)


# ───────────── Workout  ─────────────


@pytest.fixture
def workout_kwargs() -> dict:
    return {
        "PK": "USER#abc123",
        "SK": "WORKOUT#2025-11-04#W1",
        "type": "workout",
        "date": date(2025, 11, 4),
        "name": "Workout A",
        "tags": ["push", "upper"],
        "notes": "Felt strong",
        "created_at": datetime(2025, 11, 4, 18, 0, 0),
        "updated_at": datetime(2025, 11, 4, 18, 30, 0),
    }


@pytest.fixture
def make_workout(workout_kwargs):

    def _make(**overrides) -> Workout:
        data = {**workout_kwargs, **overrides}
        return Workout(**data)

    return _make


@pytest.fixture
def example_workout(make_workout) -> Workout:
    return make_workout()


@pytest.fixture
def set_kwargs() -> dict:
    return {
        "PK": "USER#abc123",
        "SK": "WORKOUT#2025-11-04#W1#SET#001",
        "type": "set",
        "exercise_id": "EXERCISE#BENCH",
        "set_number": 1,
        "reps": 8,
        "weight_kg": Decimal("60.5"),
        "rpe": 8,
        "created_at": datetime(2025, 11, 4, 18, 5, 0),
        "updated_at": datetime(2025, 11, 4, 18, 5, 30),
    }


@pytest.fixture
def make_set(set_kwargs):

    def _make(**overrides) -> WorkoutSet:
        data = {**set_kwargs, **overrides}
        return WorkoutSet(**data)

    return _make


@pytest.fixture
def example_set(make_set) -> WorkoutSet:
    return make_set()
