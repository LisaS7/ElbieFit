from datetime import date
from decimal import Decimal

import pytest

from app.models.workout import Workout
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import dates

user_sub = "abc-123"
fake_table_response = {
    "Items": [
        {
            "PK": f"USER#{user_sub}",
            "SK": "WORKOUT#2025-11-03#W2",
            "type": "workout",
            "date": "2025-11-03",
            "name": "Workout A",
            "tags": ["upper"],
            "notes": "Newer",
            "created_at": "2025-11-03T09:00:00Z",
            "updated_at": "2025-11-03T09:00:00Z",
        },
        {
            "PK": f"USER#{user_sub}",
            "SK": "WORKOUT#2025-11-01#W1",
            "type": "workout",
            "date": "2025-11-01",
            "name": "Workout B",
            "tags": ["legs"],
            "notes": "Older",
            "created_at": "2025-11-01T09:00:00Z",
            "updated_at": "2025-11-01T09:00:00Z",
        },
        {
            "PK": f"USER#{user_sub}",
            "SK": "WORKOUT#...#SET#1",
            "type": "set",
            "exercise_id": "squat",
            "set_number": 1,
            "reps": 8,
            "weight_kg": Decimal("60"),
            "rpe": 7,
            "created_at": "2025-11-03T09:00:10Z",
            "updated_at": "2025-11-03T09:00:10Z",
        },
    ]
}

# --------------- Get All ---------------


def test_get_all_for_user_returns_sorted_workouts_only(fake_table):
    fake_table.response = fake_table_response
    repo = DynamoWorkoutRepository(table=fake_table)

    workouts = repo.get_all_for_user(user_sub)

    assert len(workouts) == 2
    assert workouts[0].date.isoformat() == "2025-11-03"
    assert workouts[1].date.isoformat() == "2025-11-01"
    assert not any(w.type == "set" for w in workouts)

    # ensure query was called
    assert fake_table.last_query_kwargs is not None
    assert "KeyConditionExpression" in fake_table.last_query_kwargs


def test_get_all_for_user_empty_results_returns_empty_list(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoWorkoutRepository(fake_table)

    workouts = repo.get_all_for_user(user_sub)

    assert workouts == []


def test_to_model_raises_for_unknown_type(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoWorkoutRepository(fake_table)

    wrong_type_item = {
        "PK": "USER#abc-123",
        "SK": "WORKOUT#2025-11-03#W2",
        "type": "lunch",
    }

    with pytest.raises(ValueError) as err:
        repo._to_model(wrong_type_item)

    assert "Unknown item type" in str(err.value)


# --------------- Create ---------------


def test_create_workout_does_put_item_and_returns_workout(fake_table):
    repo = DynamoWorkoutRepository(fake_table)

    workout = Workout(
        PK="USER#test-user-sub",
        SK="WORKOUT#2025-11-16#W1",
        type="workout",
        date=date(2025, 11, 16),
        name="Leg Day for Lizards",
        tags=["legs"],
        notes="Squats until extinction",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    expected_item = workout.to_ddb_item()
    returned_item = repo.create_workout(workout)

    assert fake_table.last_put_kwargs == {"Item": expected_item}
    assert returned_item is workout
