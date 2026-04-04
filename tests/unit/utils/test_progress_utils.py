from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.utils.progress import build_exercise_progress_data, build_frequency_chart_data

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

USER_SUB = "test-user"


def _make_workout(d: date, workout_id: str = "wid1"):
    from datetime import datetime, timezone

    from app.models.workout import Workout
    from app.utils.db import build_user_pk, build_workout_sk

    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return Workout(
        PK=build_user_pk(USER_SUB),
        SK=build_workout_sk(d, workout_id),
        type="workout",
        date=d,
        name="Test Workout",
        created_at=now,
        updated_at=now,
    )


def _make_set(workout_date: date, workout_id: str, exercise_id: str, weight_kg: Decimal, set_number: int = 1):
    from datetime import datetime, timezone

    from app.models.workout import WorkoutSet
    from app.utils.db import build_set_sk, build_user_pk

    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return WorkoutSet(
        PK=build_user_pk(USER_SUB),
        SK=build_set_sk(workout_date, workout_id, set_number),
        type="set",
        exercise_id=exercise_id,
        set_number=set_number,
        reps=5,
        weight_kg=weight_kg,
        created_at=now,
        updated_at=now,
    )


# ──────────────────────────────────────────────────────────────────────────────
# build_frequency_chart_data
# ──────────────────────────────────────────────────────────────────────────────


def test_frequency_chart_returns_exactly_n_entries():
    result = build_frequency_chart_data([], weeks=12)
    assert len(result["labels"]) == 12
    assert len(result["values"]) == 12


def test_frequency_chart_all_zeros_when_no_workouts():
    result = build_frequency_chart_data([], weeks=6)
    assert result["values"] == [0, 0, 0, 0, 0, 0]


def test_frequency_chart_counts_workouts_in_current_week(monkeypatch):
    today = date.today()
    # Use two workouts in the current ISO week
    mondays_offset = today.weekday()
    this_monday = today - timedelta(days=mondays_offset)
    wednesday = this_monday + timedelta(days=2)
    friday = this_monday + timedelta(days=4)

    workouts = [_make_workout(wednesday, "w1"), _make_workout(friday, "w2")]
    result = build_frequency_chart_data(workouts, weeks=4)

    # Current week is the last entry
    assert result["values"][-1] == 2


def test_frequency_chart_workouts_in_older_weeks_are_bucketed():
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    two_weeks_ago_monday = this_monday - timedelta(weeks=2)
    two_weeks_ago_thursday = two_weeks_ago_monday + timedelta(days=3)

    workouts = [_make_workout(two_weeks_ago_thursday, "w1")]
    result = build_frequency_chart_data(workouts, weeks=4)

    # Index -3 is 2 weeks ago (index -1=current, -2=last week, -3=2 weeks ago)
    assert result["values"][-3] == 1
    # Others should be zero
    assert result["values"][-1] == 0
    assert result["values"][-2] == 0


def test_frequency_chart_workouts_outside_window_are_ignored():
    today = date.today()
    very_old = today - timedelta(weeks=52)
    workouts = [_make_workout(very_old, "w1")]
    result = build_frequency_chart_data(workouts, weeks=12)
    assert sum(result["values"]) == 0


def test_frequency_chart_label_format():
    result = build_frequency_chart_data([], weeks=1)
    # Label should be like "Mar 3" — month abbreviation + space + day without leading zero
    label = result["labels"][0]
    # Check it has a space and looks like "Mon D" or "Mon DD"
    parts = label.split(" ")
    assert len(parts) == 2
    assert parts[0].isalpha()  # month abbreviation
    assert parts[1].isdigit()  # day number


# ──────────────────────────────────────────────────────────────────────────────
# build_exercise_progress_data
# ──────────────────────────────────────────────────────────────────────────────


def test_exercise_progress_empty_when_no_sets():
    result = build_exercise_progress_data([], [], "squat", "kg")
    assert result == {"labels": [], "values": [], "unit": "kg"}


def test_exercise_progress_empty_when_no_matching_sets():
    d = date(2025, 3, 1)
    workout = _make_workout(d, "wid1")
    s = _make_set(d, "wid1", "bench", Decimal("100"), set_number=1)

    result = build_exercise_progress_data([workout], [s], "squat", "kg")
    assert result == {"labels": [], "values": [], "unit": "kg"}


def test_exercise_progress_single_set():
    d = date(2025, 3, 1)
    workout = _make_workout(d, "wid1")
    s = _make_set(d, "wid1", "squat", Decimal("80"), set_number=1)

    result = build_exercise_progress_data([workout], [s], "squat", "kg")
    assert result["labels"] == ["2025-03-01"]
    assert result["values"] == [80.0]
    assert result["unit"] == "kg"


def test_exercise_progress_multiple_sets_same_day_returns_max():
    d = date(2025, 3, 1)
    workout = _make_workout(d, "wid1")
    s1 = _make_set(d, "wid1", "squat", Decimal("70"), set_number=1)
    s2 = _make_set(d, "wid1", "squat", Decimal("90"), set_number=2)
    s3 = _make_set(d, "wid1", "squat", Decimal("85"), set_number=3)

    result = build_exercise_progress_data([workout], [s1, s2, s3], "squat", "kg")
    assert result["labels"] == ["2025-03-01"]
    assert result["values"] == [90.0]


def test_exercise_progress_sorted_by_date_ascending():
    d1 = date(2025, 1, 1)
    d2 = date(2025, 2, 1)
    d3 = date(2025, 3, 1)
    w1 = _make_workout(d1, "wid1")
    w2 = _make_workout(d2, "wid2")
    w3 = _make_workout(d3, "wid3")
    s1 = _make_set(d1, "wid1", "squat", Decimal("60"))
    s2 = _make_set(d2, "wid2", "squat", Decimal("70"))
    s3 = _make_set(d3, "wid3", "squat", Decimal("80"))

    result = build_exercise_progress_data([w3, w1, w2], [s3, s1, s2], "squat", "kg")
    assert result["labels"] == ["2025-01-01", "2025-02-01", "2025-03-01"]
    assert result["values"] == [60.0, 70.0, 80.0]


def test_exercise_progress_kg_to_lb_conversion():
    d = date(2025, 3, 1)
    workout = _make_workout(d, "wid1")
    s = _make_set(d, "wid1", "squat", Decimal("100"), set_number=1)

    result = build_exercise_progress_data([workout], [s], "squat", "lb")
    assert result["unit"] == "lb"
    # 100 kg * 2.2046... ≈ 220.46
    assert abs(result["values"][0] - 220.46) < 0.1


def test_exercise_progress_sets_without_weight_are_ignored():
    d = date(2025, 3, 1)
    workout = _make_workout(d, "wid1")
    # Set with no weight
    from datetime import datetime, timezone

    from app.models.workout import WorkoutSet
    from app.utils.db import build_set_sk, build_user_pk

    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    s_no_weight = WorkoutSet(
        PK=build_user_pk(USER_SUB),
        SK=build_set_sk(d, "wid1", 1),
        type="set",
        exercise_id="squat",
        set_number=1,
        reps=5,
        weight_kg=None,
        created_at=now,
        updated_at=now,
    )

    result = build_exercise_progress_data([workout], [s_no_weight], "squat", "kg")
    assert result == {"labels": [], "values": [], "unit": "kg"}


def test_exercise_progress_unit_preserved_in_result():
    result = build_exercise_progress_data([], [], "squat", "lb")
    assert result["unit"] == "lb"
