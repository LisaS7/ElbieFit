from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.models.exercise import Exercise
from app.models.workout import Workout, WorkoutSet
from app.utils.units import kg_to_lb


def build_frequency_chart_data(workouts: list[Workout], weeks: int = 12) -> dict:
    """
    Return workout frequency bucketed by ISO week for the last N weeks.

    Returns {"labels": ["Mar 3", ...], "values": [4, 2, ...]} where each
    entry corresponds to one Mon–Sun week, oldest first.
    """
    today = date.today()

    # Find the Monday of the current ISO week
    current_week_monday = today - timedelta(days=today.weekday())

    # Build the list of week-start Mondays for the last N weeks (oldest first)
    week_starts = [
        current_week_monday - timedelta(weeks=offset)
        for offset in range(weeks - 1, -1, -1)
    ]

    # Count workouts per week
    counts: dict[date, int] = {ws: 0 for ws in week_starts}
    for workout in workouts:
        # Find the Monday of this workout's week
        workout_monday = workout.date - timedelta(days=workout.date.weekday())
        if workout_monday in counts:
            counts[workout_monday] += 1

    labels = [ws.strftime("%b %-d") for ws in week_starts]
    values = [counts[ws] for ws in week_starts]

    return {"labels": labels, "values": values}


def build_exercise_progress_data(
    sets: list[WorkoutSet],
    exercise_id: str,
    weight_unit: str,
) -> dict:
    """
    Return max weight per workout date for the given exercise.

    Returns {"labels": ["2025-01-04", ...], "values": [80.0, ...], "unit": "kg"}.
    Returns empty lists if no matching sets exist.

    Date is parsed directly from the set SK
    (format: WORKOUT#<date>#<workout_id>#SET#<n> — date is parts[1]).
    """
    date_max_kg: dict[date, Decimal] = {}
    for s in sets:
        if s.exercise_id != exercise_id:
            continue
        if s.weight_kg is None:
            continue

        parts = s.SK.split("#")
        if len(parts) < 3:
            continue
        try:
            workout_date = date.fromisoformat(parts[1])
        except ValueError:
            continue

        if workout_date not in date_max_kg or s.weight_kg > date_max_kg[workout_date]:
            date_max_kg[workout_date] = s.weight_kg

    if not date_max_kg:
        return {"labels": [], "values": [], "unit": weight_unit}

    sorted_dates = sorted(date_max_kg.keys())

    labels = [d.isoformat() for d in sorted_dates]
    values = []
    for d in sorted_dates:
        kg = date_max_kg[d]
        if weight_unit == "lb":
            converted = float(kg_to_lb(kg))
        else:
            converted = float(kg)
        values.append(round(converted, 2))

    return {"labels": labels, "values": values, "unit": weight_unit}


def build_volume_chart_data(
    sets: list[WorkoutSet],
    weight_unit: str,
    weeks: int = 12,
    exercise_id: str | None = None,
) -> dict:
    """
    Return total volume (sets × reps × weight) bucketed by ISO week for the last N weeks.

    Returns {"labels": ["Mar 3", ...], "values": [1250.0, ...], "unit": "kg"|"lb"}.
    Date is parsed directly from the set SK (parts[1]).
    """
    today = date.today()
    current_week_monday = today - timedelta(days=today.weekday())
    week_starts = [
        current_week_monday - timedelta(weeks=offset)
        for offset in range(weeks - 1, -1, -1)
    ]

    filtered_sets = [s for s in sets if s.exercise_id == exercise_id] if exercise_id else sets

    volume_kg: dict[date, Decimal] = {ws: Decimal(0) for ws in week_starts}
    for s in filtered_sets:
        if s.weight_kg is None:
            continue
        parts = s.SK.split("#")
        if len(parts) < 3:
            continue
        try:
            workout_date = date.fromisoformat(parts[1])
        except ValueError:
            continue
        workout_monday = workout_date - timedelta(days=workout_date.weekday())
        if workout_monday not in volume_kg:
            continue
        volume_kg[workout_monday] += s.weight_kg * s.reps

    labels = [ws.strftime("%b %-d") for ws in week_starts]
    values = []
    for ws in week_starts:
        kg = volume_kg[ws]
        if weight_unit == "lb":
            values.append(round(float(kg_to_lb(kg)), 1))
        else:
            values.append(round(float(kg), 1))

    return {"labels": labels, "values": values, "unit": weight_unit}


def build_1rm_chart_data(
    sets: list[WorkoutSet],
    exercise_id: str,
    weight_unit: str,
) -> dict:
    """
    Return estimated 1RM over time for a given exercise.

    Formula: weight × (1 + reps / 30), max per workout date.
    Returns {"labels": [...], "values": [...], "unit": "kg"|"lb"}.
    Date is parsed directly from the set SK (parts[1]).
    """
    date_max_1rm: dict[date, Decimal] = {}
    for s in sets:
        if s.exercise_id != exercise_id:
            continue
        if s.weight_kg is None or s.reps == 0:
            continue
        parts = s.SK.split("#")
        if len(parts) < 3:
            continue
        try:
            workout_date = date.fromisoformat(parts[1])
        except ValueError:
            continue
        estimated = s.weight_kg * (1 + Decimal(s.reps) / 30)
        if workout_date not in date_max_1rm or estimated > date_max_1rm[workout_date]:
            date_max_1rm[workout_date] = estimated

    if not date_max_1rm:
        return {"labels": [], "values": [], "unit": weight_unit}

    sorted_dates = sorted(date_max_1rm.keys())
    labels = [d.isoformat() for d in sorted_dates]
    values = []
    for d in sorted_dates:
        kg = date_max_1rm[d]
        if weight_unit == "lb":
            values.append(round(float(kg_to_lb(kg)), 2))
        else:
            values.append(round(float(kg), 2))

    return {"labels": labels, "values": values, "unit": weight_unit}


def build_distribution_chart_data(
    sets: list[WorkoutSet],
    exercises: list[Exercise],
) -> dict:
    """
    Return set counts broken down by muscle group and by exercise name (top 10 + Other).

    Returns:
        {
            "by_muscle":   {"labels": [...], "values": [...]},
            "by_exercise": {"labels": [...], "values": [...]},
        }
    """
    exercise_map = {e.exercise_id: e for e in exercises}

    muscle_counts: dict[str, int] = defaultdict(int)
    exercise_counts: dict[str, int] = defaultdict(int)

    for s in sets:
        ex = exercise_map.get(s.exercise_id)
        if ex is None:
            continue
        exercise_counts[ex.name] += 1
        for muscle in ex.muscles:
            muscle_counts[muscle] += 1

    def _top10_with_other(counts: dict[str, int]) -> dict:
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top = sorted_items[:10]
        rest = sum(v for _, v in sorted_items[10:])
        labels = [k for k, _ in top]
        values = [v for _, v in top]
        if rest:
            labels.append("Other")
            values.append(rest)
        return {"labels": labels, "values": values}

    return {
        "by_muscle": _top10_with_other(muscle_counts),
        "by_exercise": _top10_with_other(exercise_counts),
    }
