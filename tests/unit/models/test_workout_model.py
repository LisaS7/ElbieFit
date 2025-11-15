from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.workout import Workout, WorkoutSet

# ------------ Helpers ------------


def make_example_workout(**overrides) -> Workout:
    base = {
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
    base.update(overrides)
    return Workout(**base)


def make_example_workout_set(**overrides) -> WorkoutSet:
    base = {
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
    base.update(overrides)
    return WorkoutSet(**base)


# ------------ Workout tests ------------


def test_workout_model_creates_instance_with_expected_fields():
    workout = make_example_workout()

    assert workout.PK == "USER#abc123"
    assert workout.SK == "WORKOUT#2025-11-04#W1"
    assert workout.type == "workout"
    assert workout.date == date(2025, 11, 4)
    assert workout.tags == ["push", "upper"]
    assert workout.notes == "Felt strong"
    assert isinstance(workout.created_at, datetime)
    assert isinstance(workout.updated_at, datetime)


def test_workout_type_must_be_literal_workout():
    with pytest.raises(ValidationError):
        make_example_workout(type="cardio")


def test_workout_notes_is_optional_and_can_be_none():
    workout = make_example_workout(notes=None)
    assert workout.notes is None


def test_workout_to_ddb_item_uses_date_and_dt_helpers(monkeypatch):
    # Track calls to fake converters
    date_calls = []
    dt_calls = []

    def fake_date_to_iso(d: date) -> str:
        date_calls.append(d)
        return f"DATE-{d:%Y%m%d}"

    def fake_dt_to_iso(dt: datetime) -> str:
        dt_calls.append(dt)
        return f"DT-{dt:%Y%m%d%H%M%S}"

    # Patch inside the workout module
    monkeypatch.setattr("app.models.workout.date_to_iso", fake_date_to_iso)
    monkeypatch.setattr("app.models.workout.dt_to_iso", fake_dt_to_iso)

    workout_date = date(2025, 11, 4)
    created_at = datetime(2025, 11, 4, 18, 0, 0)
    updated_at = datetime(2025, 11, 4, 18, 30, 0)

    workout = make_example_workout(
        date=workout_date,
        created_at=created_at,
        updated_at=updated_at,
    )

    item = workout.to_ddb_item()

    # The dict has the converted values, not raw datetimes
    assert item["date"] == "DATE-20251104"
    assert item["created_at"] == "DT-20251104180000"
    assert item["updated_at"] == "DT-20251104183000"

    # Sanity check: no datetime objects sneak through
    assert not isinstance(item["date"], date)
    assert not isinstance(item["created_at"], datetime)
    assert not isinstance(item["updated_at"], datetime)


# ------------ WorkoutSet tests ------------


def test_workout_set_model_creates_instance_with_expected_fields():
    ws = make_example_workout_set()

    assert ws.PK == "USER#abc123"
    assert ws.SK.startswith("WORKOUT#2025-11-04#W1#SET#")
    assert ws.type == "set"
    assert ws.exercise_id == "EXERCISE#BENCH"
    assert ws.set_number == 1
    assert ws.reps == 8
    assert ws.weight_kg == Decimal("60.5")
    assert ws.rpe == 8
    assert isinstance(ws.created_at, datetime)
    assert isinstance(ws.updated_at, datetime)


def test_workout_set_type_must_be_literal_set():
    with pytest.raises(ValidationError):
        make_example_workout_set(type="workout")  # not allowed per Literal


def test_workout_set_to_ddb_item_uses_dt_helper(monkeypatch):
    dt_calls = []

    def fake_dt_to_iso(dt: datetime) -> str:
        dt_calls.append(dt)
        return f"DT-{dt:%Y%m%d%H%M%S}"

    monkeypatch.setattr("app.models.workout.dt_to_iso", fake_dt_to_iso)

    created_at = datetime(2025, 11, 4, 18, 5, 0)
    updated_at = datetime(2025, 11, 4, 18, 5, 30)

    ws = make_example_workout_set(
        created_at=created_at,
        updated_at=updated_at,
    )

    item = ws.to_ddb_item()

    # Helpers used for both timestamps
    assert item["created_at"] == "DT-20251104180500"
    assert item["updated_at"] == "DT-20251104180530"

    # Decimal should still be Decimal (model_dump keeps it)
    assert isinstance(item["weight_kg"], Decimal)

    # And no datetime objects in the final dict
    assert not isinstance(item["created_at"], datetime)
    assert not isinstance(item["updated_at"], datetime)
