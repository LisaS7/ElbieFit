from datetime import date, timedelta
from decimal import Decimal

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
    workouts: list[Workout],
    sets: list[WorkoutSet],
    exercise_id: str,
    weight_unit: str,
) -> dict:
    """
    Return max weight per workout date for the given exercise.

    Returns {"labels": ["2025-01-04", ...], "values": [80.0, ...], "unit": "kg"}.
    Returns empty lists if no matching sets exist.

    Sets are joined to workouts via workout_id extracted from the set SK
    (format: WORKOUT#<date>#<workout_id>#SET#<n> — workout_id is parts[2]).
    """
    # Build a map from workout_id → date
    workout_date_map: dict[str, date] = {w.workout_id: w.date for w in workouts}

    # Filter sets for this exercise and group max weight_kg by workout date
    date_max_kg: dict[date, Decimal] = {}
    for s in sets:
        if s.exercise_id != exercise_id:
            continue
        if s.weight_kg is None:
            continue

        parts = s.SK.split("#")
        if len(parts) < 3:
            continue
        workout_id = parts[2]

        workout_date = workout_date_map.get(workout_id)
        if workout_date is None:
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
