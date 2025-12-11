from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.exercise import Exercise
from app.models.profile import UserProfile
from app.models.workout import Workout, WorkoutSet

# ───────────── Exercise  ─────────────


@pytest.fixture
def exercise():
    """Factory fixture for Exercise instances."""

    def _make(**overrides):
        defaults = {
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
        return Exercise(**{**defaults, **overrides})

    return _make


@pytest.fixture
def example_exercise(exercise):
    return exercise()


# ───────────── Profile  ─────────────
@pytest.fixture
def profile():
    """Factory fixture for UserProfile instances."""

    def _make(**overrides):
        defaults = {
            "PK": "USER#123",
            "SK": "PROFILE",
            "display_name": "Lisa Test",
            "email": "lisa@example.com",
            "created_at": datetime(2025, 1, 1, 12, 0, 0),
            "updated_at": datetime(2025, 1, 1, 13, 0, 0),
            "timezone": "Europe/London",
        }
        return UserProfile(**{**defaults, **overrides})

    return _make


@pytest.fixture
def example_profile(profile):
    return profile()


# ───────────── Workout  ─────────────


@pytest.fixture
def workout():
    """Factory fixture for Workout instances."""

    def _make(**overrides):
        defaults = {
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
        return Workout(**{**defaults, **overrides})

    return _make


@pytest.fixture
def example_workout(workout):
    """Default Workout instance for tests that don't need customization."""
    return workout()


# ───────────── WorkoutSet  ─────────────


@pytest.fixture
def workout_set():
    """Factory fixture for WorkoutSet instances."""

    def _make(**overrides):
        defaults = {
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
        return WorkoutSet(**{**defaults, **overrides})

    return _make


@pytest.fixture
def example_set(workout_set):
    """Default WorkoutSet instance for tests that don't need customization."""
    return workout_set()
