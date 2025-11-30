import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.workout import Workout, WorkoutCreate, WorkoutSet
from app.repositories.errors import WorkoutNotFoundError, WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import dates, db

user_sub = "abc-123"
fake_table_response = {
    "Items": [
        # Workout W2
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
        # Workout W1
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
        # A set for W2
        {
            "PK": f"USER#{user_sub}",
            "SK": "WORKOUT#2025-11-03#W2#SET#1",
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


# --------------- To Model ---------------


def test_to_model_wraps_validation_error_in_workoutrepoerror(fake_table):
    # No required fields -> Pydantic should blow up
    bad_item = {
        "PK": "USER#abc-123",
        "SK": "WORKOUT#2025-11-03#W2",
        "type": "workout",
        # missing date, name, etc.
    }

    repo = DynamoWorkoutRepository(table=fake_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo._to_model(bad_item)

    assert "Failed to create workout model" in str(excinfo.value)


def test_to_model_raises_for_unknown_type(fake_table):
    repo = DynamoWorkoutRepository(fake_table)

    wrong_type_item = {
        "PK": "USER#abc-123",
        "SK": "WORKOUT#2025-11-03#W2",
        "type": "lunch",
    }

    with pytest.raises(WorkoutRepoError) as err:
        repo._to_model(wrong_type_item)

    assert "Unknown item type" in str(err.value)


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


def test_get_all_for_user_raises_repoerror_on_client_error(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_for_user("abc-123")

    assert "Failed to query database for workouts" in str(excinfo.value)


def test_get_all_for_user_raises_repoerror_on_parse_error(bad_items_table):
    repo = DynamoWorkoutRepository(table=bad_items_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_for_user("abc-123")

    assert "Failed to parse workouts from database response" in str(excinfo.value)


# --------------- Get workout and sets ---------------


def test_get_workout_with_sets_returns_workout_and_sets(fake_table):
    fake_table.response = fake_table_response
    repo = DynamoWorkoutRepository(table=fake_table)

    workout_date = date(2025, 11, 3)
    workout_id = "W2"
    pk = f"USER#{user_sub}"

    workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)

    assert workout.SK == "WORKOUT#2025-11-03#W2"
    assert workout.PK == pk
    assert workout.name == "Workout A"
    assert workout.date.isoformat() == "2025-11-03"

    # Check sets
    assert len(sets) == 1
    s = sets[0]
    assert isinstance(s, WorkoutSet)
    assert s.exercise_id == "squat"
    assert s.reps == 8
    assert s.weight_kg == Decimal("60")

    # Optional: verify the query was applied
    assert "KeyConditionExpression" in fake_table.last_query_kwargs


def test_get_workout_with_sets_raises_error_when_not_found(fake_table):
    workout_date = date(2025, 11, 3)
    workout_id = "DOES_NOT_EXIST"

    fake_table.response = {"Items": []}

    repo = DynamoWorkoutRepository(table=fake_table)

    with pytest.raises(WorkoutNotFoundError) as excinfo:
        repo.get_workout_with_sets(user_sub, workout_date, workout_id)

    assert "not found" in str(excinfo.value)


def test_get_workout_with_sets_raises_repoerror_on_client_error(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets("abc-123", date(2025, 11, 3), "W2")

    assert "Failed to query workout and sets from database" in str(excinfo.value)


def test_get_workout_with_sets_raises_repoerror_on_parse_error(bad_items_table):
    repo = DynamoWorkoutRepository(table=bad_items_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets("abc-123", date(2025, 11, 3), "W2")

    assert "Failed to parse workout and sets from response" in str(excinfo.value)


# --------------- Create ---------------


def test_create_workout_does_put_item_and_returns_workout(fake_table, monkeypatch):
    user_sub = "abc-123"
    workout_date = date(2025, 11, 16)

    fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    from app.repositories import workout as workout_repo_module

    monkeypatch.setattr(workout_repo_module.uuid, "uuid4", lambda: fixed_uuid)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(fake_table)
    data = WorkoutCreate(date=workout_date, name="Bench Party")
    workout = repo.create_workout(user_sub=user_sub, data=data)

    # Check PK/SK are built correctly
    assert workout.PK == db.build_user_pk(user_sub)
    assert workout.SK == db.build_workout_sk(workout_date, str(fixed_uuid))
    assert workout.type == "workout"
    assert workout.date == workout_date
    assert workout.name == "Bench Party"
    assert workout.created_at == fixed_now
    assert workout.updated_at == fixed_now

    # Check the item was written to Dynamo
    assert fake_table.last_put_kwargs == {"Item": workout.to_ddb_item()}


def test_create_workout_raises_repoerror_on_client_error(failing_put_table):
    repo = DynamoWorkoutRepository(table=failing_put_table)
    user_sub = "abc-123"
    data = WorkoutCreate(
        date=date(2025, 11, 16),
        name="Boom Day",
    )
    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.create_workout(user_sub, data)

    assert "Failed to create workout in database" in str(excinfo.value)


# --------------- Update ---------------


def test_update_workout_does_put_item_and_returns_workout(fake_table):
    repo = DynamoWorkoutRepository(fake_table)

    workout = Workout(
        PK="USER#test-user-sub",
        SK="WORKOUT#2025-11-16#W1",
        type="workout",
        date=date(2025, 11, 16),
        name="Updated Lizard Leg Day",
        tags=["legs", "updated"],
        notes="Now with extra squats",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    expected_item = workout.to_ddb_item()
    returned_item = repo.update_workout(workout)

    assert fake_table.last_put_kwargs == {"Item": expected_item}
    assert returned_item is workout


def test_update_workout_raises_repoerror_on_client_error(failing_put_table):
    repo = DynamoWorkoutRepository(table=failing_put_table)
    workout = Workout(
        PK="USER#abc-123",
        SK="WORKOUT#2025-11-16#W1",
        type="workout",
        date=date(2025, 11, 16),
        name="Updated",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.update_workout(workout)

    assert "Failed to update workout in database" in str(excinfo.value)


# --------------- Delete ---------------


def test_delete_workout_and_sets_deletes_workout_and_its_sets(fake_table):
    """
    Given a workout with sets, delete_workout_and_sets should:
      - query using the correct PK and SK prefix
      - delete all returned items via batch_writer
    """
    repo = DynamoWorkoutRepository(table=fake_table)

    workout_date = date(2025, 11, 3)
    workout_id = "W2"
    pk = f"USER#{user_sub}"

    # Only include the workout + its sets in this fake response
    fake_table.response = {
        "Items": [
            {
                "PK": pk,
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
                "PK": pk,
                "SK": "WORKOUT#2025-11-03#W2#SET#1",
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

    repo.delete_workout_and_sets(user_sub, workout_date, workout_id)

    # Check that all items from the fake response were "deleted"
    assert len(fake_table.deleted_keys) == 2
    assert {"PK": pk, "SK": "WORKOUT#2025-11-03#W2"} in fake_table.deleted_keys
    assert {
        "PK": pk,
        "SK": "WORKOUT#2025-11-03#W2#SET#1",
    } in fake_table.deleted_keys


def test_delete_workout_and_sets_does_nothing_when_no_items(fake_table):
    """
    If Dynamo returns no items, the method should return quietly
    and not attempt any deletes.
    """
    repo = DynamoWorkoutRepository(table=fake_table)

    workout_date = date(2025, 11, 3)
    workout_id = "NON_EXISTENT"

    fake_table.response = {"Items": []}

    repo.delete_workout_and_sets(user_sub, workout_date, workout_id)

    # Query should still be called
    assert fake_table.last_query_kwargs is not None

    # But no deletes should be recorded
    assert fake_table.deleted_keys == []


def test_delete_workout_and_sets_raises_repoerror_on_client_error(failing_delete_table):
    repo = DynamoWorkoutRepository(table=failing_delete_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.delete_workout_and_sets("abc-123", date(2025, 11, 3), "W2")

    assert "Failed to delete workout and sets from database" in str(excinfo.value)
