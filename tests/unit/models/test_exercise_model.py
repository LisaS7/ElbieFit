from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.exercise import Exercise


def make_example_exercise(**overrides) -> Exercise:
    """Helper to reduce repetition in tests."""
    base = {
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
    base.update(overrides)
    return Exercise(**base)


def test_exercise_model_creates_instance_with_expected_fields():
    exercise = make_example_exercise()

    assert exercise.PK == "EXERCISE#PUSHUP"
    assert exercise.SK == "EXERCISE#PUSHUP"
    assert exercise.type == "exercise"
    assert exercise.name == "Push-up"
    assert exercise.muscles == ["chest", "triceps"]
    assert exercise.equipment == "bodyweight"
    assert exercise.category == "strength"
    assert isinstance(exercise.created_at, datetime)
    assert isinstance(exercise.updated_at, datetime)


def test_exercise_type_must_be_literal_exercise():
    # type is a Literal["exercise"], so anything else should blow up
    with pytest.raises(ValidationError):
        make_example_exercise(type="banana")


def test_exercise_category_is_optional_and_defaults_to_none():
    exercise = make_example_exercise(category=None)
    assert exercise.category is None


def test_to_ddb_item_converts_datetimes_using_dt_to_iso(monkeypatch):
    # patch dt_to_iso inside the exercise module so we can
    # (a) prove it's called, and (b) control the return value.
    calls = []

    def fake_dt_to_iso(dt: datetime) -> str:
        calls.append(dt)
        # recognisable fake format so we know it came from here
        return f"ISO-{dt:%Y%m%d%H%M%S}"

    monkeypatch.setattr(
        "app.models.exercise.dt_to_iso",
        fake_dt_to_iso,
    )

    created_at = datetime(2025, 1, 1, 12, 0, 0)
    updated_at = datetime(2025, 1, 2, 13, 30, 0)

    exercise = make_example_exercise(
        created_at=created_at,
        updated_at=updated_at,
    )

    item = exercise.to_ddb_item()

    # The dict has the converted values, not raw datetimes
    assert item["created_at"] == "ISO-20250101120000"
    assert item["updated_at"] == "ISO-20250102133000"

    # Sanity check: no datetime objects sneak through
    assert not isinstance(item["created_at"], datetime)
    assert not isinstance(item["updated_at"], datetime)
