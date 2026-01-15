from datetime import datetime

import pytest
from pydantic import ValidationError


def test_exercise_model_creates_instance_with_expected_fields(example_exercise):

    assert example_exercise.PK == "EXERCISE#PUSHUP"
    assert example_exercise.SK == "EXERCISE#PUSHUP"
    assert example_exercise.type == "exercise"
    assert example_exercise.name == "Push-up"
    assert example_exercise.muscles == ["chest", "triceps"]
    assert example_exercise.equipment == "bodyweight"
    assert example_exercise.category == "push"
    assert isinstance(example_exercise.created_at, datetime)
    assert isinstance(example_exercise.updated_at, datetime)


def test_exercise_id_comes_from_suffix_of_SK(exercise):
    ex = exercise(SK="EXERCISE#1234-uuid")
    assert ex.exercise_id == "1234-uuid"


def test_exercise_type_must_be_literal_exercise(exercise):
    # type is a Literal["exercise"], so anything else should blow up
    with pytest.raises(ValidationError):
        exercise(type="banana")


def test_exercise_category_is_optional_and_defaults_to_none(exercise):
    ex = exercise(category=None)
    assert ex.category is None


def test_invalid_category_raises_validation_error(exercise):
    with pytest.raises(ValidationError):
        exercise(category="strength")


def test_to_ddb_item_converts_datetimes_using_dt_to_iso(monkeypatch, exercise):
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

    ex = exercise(
        created_at=created_at,
        updated_at=updated_at,
    )

    item = ex.to_ddb_item()

    # The dict has the converted values, not raw datetimes
    assert item["created_at"] == "ISO-20250101120000"
    assert item["updated_at"] == "ISO-20250102133000"

    # Sanity check: no datetime objects sneak through
    assert not isinstance(item["created_at"], datetime)
    assert not isinstance(item["updated_at"], datetime)


def test_invalid_equipment_raises_validation_error(exercise):
    with pytest.raises(ValidationError) as exc:
        exercise(equipment="definitely-not-real-equipment")

    # Optional: check it’s the specific field that failed
    errors = exc.value.errors()
    assert any(e["loc"] == ("equipment",) for e in errors)


def test_invalid_muscle_raises_validation_error(exercise):
    with pytest.raises(ValidationError) as exc:
        exercise(muscles=["chest", "mystery-muscle"])

    errors = exc.value.errors()
    assert any(e["loc"] == ("muscles",) for e in errors)
