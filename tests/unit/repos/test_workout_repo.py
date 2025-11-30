import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.workout import Workout, WorkoutCreate, WorkoutSet
from app.repositories.errors import RepoError, WorkoutNotFoundError, WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import dates, db

USER_SUB = "abc-123"
WORKOUT_DATE_W2 = date(2025, 11, 3)
WORKOUT_ID_W2 = "W2"
WORKOUT_DATE_NEW = date(2025, 11, 16)

WORKOUT_W2_ITEM = {
    "PK": f"USER#{USER_SUB}",
    "SK": "WORKOUT#2025-11-03#W2",
    "type": "workout",
    "date": "2025-11-03",
    "name": "Workout A",
    "tags": ["upper"],
    "notes": "Newer",
    "created_at": "2025-11-03T09:00:00Z",
    "updated_at": "2025-11-03T09:00:00Z",
}

WORKOUT_W1_ITEM = {
    "PK": f"USER#{USER_SUB}",
    "SK": "WORKOUT#2025-11-01#W1",
    "type": "workout",
    "date": "2025-11-01",
    "name": "Workout B",
    "tags": ["legs"],
    "notes": "Older",
    "created_at": "2025-11-01T09:00:00Z",
    "updated_at": "2025-11-01T09:00:00Z",
}

WORKOUT_W2_SET1_ITEM = {
    "PK": f"USER#{USER_SUB}",
    "SK": "WORKOUT#2025-11-03#W2#SET#1",
    "type": "set",
    "exercise_id": "squat",
    "set_number": 1,
    "reps": 8,
    "weight_kg": Decimal("60"),
    "rpe": 7,
    "created_at": "2025-11-03T09:00:10Z",
    "updated_at": "2025-11-03T09:00:10Z",
}

FAKE_TABLE_RESPONSE_ALL = {
    "Items": [
        WORKOUT_W2_ITEM,
        WORKOUT_W1_ITEM,
        WORKOUT_W2_SET1_ITEM,
    ]
}

FAKE_TABLE_RESPONSE_W2_ONLY = {
    "Items": [
        WORKOUT_W2_ITEM,
        WORKOUT_W2_SET1_ITEM,
    ]
}


# --------------- To Model ---------------


def test_to_model_wraps_validation_error_in_workoutrepoerror(fake_table):
    # No required fields -> Pydantic should blow up
    bad_item = {
        "PK": f"USER#{USER_SUB}",
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
    fake_table.response = FAKE_TABLE_RESPONSE_ALL
    repo = DynamoWorkoutRepository(table=fake_table)

    workouts = repo.get_all_for_user(USER_SUB)

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

    workouts = repo.get_all_for_user(USER_SUB)

    assert workouts == []


def test_get_all_for_user_raises_repoerror_on_client_error(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(RepoError) as excinfo:
        repo.get_all_for_user(USER_SUB)

    assert "Failed to query database" in str(excinfo.value)


def test_get_all_for_user_raises_repoerror_on_parse_error(bad_items_table):
    repo = DynamoWorkoutRepository(table=bad_items_table)

    with pytest.raises(RepoError) as excinfo:
        repo.get_all_for_user(USER_SUB)

    assert "Failed to create workout model from item" in str(excinfo.value)


# --------------- Get workout and sets ---------------


def test_get_workout_with_sets_returns_workout_and_sets(fake_table):
    fake_table.response = FAKE_TABLE_RESPONSE_ALL
    repo = DynamoWorkoutRepository(table=fake_table)

    workout, sets = repo.get_workout_with_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert workout.SK == "WORKOUT#2025-11-03#W2"
    assert workout.PK == f"USER#{USER_SUB}"
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
    workout_id = "DOES_NOT_EXIST"

    fake_table.response = {"Items": []}

    repo = DynamoWorkoutRepository(table=fake_table)

    with pytest.raises(WorkoutNotFoundError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, WORKOUT_DATE_W2, workout_id)

    assert "not found" in str(excinfo.value)


def test_get_workout_with_sets_raises_repoerror_on_client_error(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(RepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to query workout and sets from database" in str(excinfo.value)


def test_get_workout_with_sets_raises_repoerror_on_parse_error(bad_items_table):
    repo = DynamoWorkoutRepository(table=bad_items_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to create workout model from item" in str(excinfo.value)


# --------------- Create ---------------


def test_create_workout_does_put_item_and_returns_workout(fake_table, monkeypatch):
    fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    from app.repositories import workout as workout_repo_module

    monkeypatch.setattr(workout_repo_module.uuid, "uuid4", lambda: fixed_uuid)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(fake_table)
    data = WorkoutCreate(date=WORKOUT_DATE_NEW, name="Bench Party")
    workout = repo.create_workout(user_sub=USER_SUB, data=data)

    # Check PK/SK are built correctly
    assert workout.PK == db.build_user_pk(USER_SUB)
    assert workout.SK == db.build_workout_sk(WORKOUT_DATE_NEW, str(fixed_uuid))
    assert workout.type == "workout"
    assert workout.date == WORKOUT_DATE_NEW
    assert workout.name == "Bench Party"
    assert workout.created_at == fixed_now
    assert workout.updated_at == fixed_now

    # Check the item was written to Dynamo
    assert fake_table.last_put_kwargs == {"Item": workout.to_ddb_item()}


def test_create_workout_raises_repoerror_on_client_error(failing_put_table):
    repo = DynamoWorkoutRepository(table=failing_put_table)
    data = WorkoutCreate(
        date=WORKOUT_DATE_NEW,
        name="Boom Day",
    )
    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.create_workout(USER_SUB, data)

    assert "Failed to create workout in database" in str(excinfo.value)


# --------------- Update (No New SK) ---------------


def test_update_workout_does_put_item_and_returns_workout(fake_table):
    repo = DynamoWorkoutRepository(fake_table)

    workout = Workout(
        PK="USER#test-user-sub",
        SK="WORKOUT#2025-11-16#W1",
        type="workout",
        date=WORKOUT_DATE_NEW,
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
        date=WORKOUT_DATE_NEW,
        name="Updated",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.update_workout(workout)

    assert "Failed to update workout in database" in str(excinfo.value)


# --------------- Update (New SK) ---------------
def test_move_workout_date_moves_workout_without_sets(fake_table, monkeypatch):
    from app.repositories import workout as workout_repo_module

    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(fake_table)

    # Original workout on old date
    workout = Workout(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2),
        type="workout",
        date=WORKOUT_DATE_W2,
        name="Move Me Dino Day",
        tags=["upper"],
        notes="Roar",
        created_at=fixed_now,
        updated_at=fixed_now,
    )

    # Spy on delete_workout_and_sets so we don't rely on its own implementation
    delete_calls = {}

    def fake_delete(user_sub, workout_date, workout_id):
        delete_calls["user_sub"] = user_sub
        delete_calls["date"] = workout_date
        delete_calls["workout_id"] = workout_id

    monkeypatch.setattr(repo, "delete_workout_and_sets", fake_delete)

    # Act: move the workout to a new date, but with no sets
    repo.move_workout_date(
        user_sub=USER_SUB,
        workout=workout,
        new_date=WORKOUT_DATE_NEW,
        sets=[],
    )

    # ── Assert: delete called with OLD keys ──
    assert delete_calls == {
        "user_sub": USER_SUB,
        "date": WORKOUT_DATE_W2,
        "workout_id": WORKOUT_ID_W2,
    }

    # ── Assert: new workout item was written with NEW keys ──
    expected_pk = db.build_user_pk(USER_SUB)
    expected_sk = db.build_workout_sk(WORKOUT_DATE_NEW, WORKOUT_ID_W2)

    expected_workout = workout.model_copy(
        update={
            "PK": expected_pk,
            "SK": expected_sk,
            "date": WORKOUT_DATE_NEW,
            "updated_at": fixed_now,
        }
    )

    assert fake_table.last_put_kwargs == {"Item": expected_workout.to_ddb_item()}


def test_move_workout_date_recreates_sets_with_new_keys(fake_table, monkeypatch):
    from app.repositories import workout as workout_repo_module

    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(fake_table)

    # Original workout
    workout = Workout(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2),
        type="workout",
        date=WORKOUT_DATE_W2,
        name="Leg Day Before Meteor",
        tags=["legs"],
        notes=None,
        created_at=fixed_now,
        updated_at=fixed_now,
    )

    # Original set on old keys
    set1 = WorkoutSet(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_set_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2, 1),
        type="set",
        exercise_id="squat",
        set_number=1,
        reps=8,
        weight_kg=Decimal("60"),
        rpe=7,
        created_at=fixed_now,
        updated_at=fixed_now,
    )

    # Spy on delete again (we only care that it's called, not what it does internally)
    delete_calls = {}

    def fake_delete(user_sub, workout_date, workout_id):
        delete_calls["user_sub"] = user_sub
        delete_calls["date"] = workout_date
        delete_calls["workout_id"] = workout_id

    monkeypatch.setattr(repo, "delete_workout_and_sets", fake_delete)

    # Act: move with one set
    repo.move_workout_date(
        user_sub=USER_SUB,
        workout=workout,
        new_date=WORKOUT_DATE_NEW,
        sets=[set1],
    )

    # ── Assert: delete called on old workout ──
    assert delete_calls == {
        "user_sub": USER_SUB,
        "date": WORKOUT_DATE_W2,
        "workout_id": WORKOUT_ID_W2,
    }

    # ── Assert: the last Dynamo put is the recreated set with new PK/SK ──
    expected_pk = db.build_user_pk(USER_SUB)
    expected_sk = db.build_set_sk(WORKOUT_DATE_NEW, WORKOUT_ID_W2, 1)

    expected_set_item = {
        **set1.to_ddb_item(),
        "PK": expected_pk,
        "SK": expected_sk,
    }

    assert fake_table.last_put_kwargs == {"Item": expected_set_item}


# --------------- Delete ---------------


def test_delete_workout_and_sets_deletes_workout_and_its_sets(fake_table):
    """
    Given a workout with sets, delete_workout_and_sets should:
      - query using the correct PK and SK prefix
      - delete all returned items via batch_writer
    """
    repo = DynamoWorkoutRepository(table=fake_table)

    # Only include the workout + its sets in this fake response
    fake_table.response = FAKE_TABLE_RESPONSE_W2_ONLY
    repo.delete_workout_and_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    # Check that all items from the fake response were "deleted"
    assert len(fake_table.deleted_keys) == 2
    assert {
        "PK": f"USER#{USER_SUB}",
        "SK": "WORKOUT#2025-11-03#W2",
    } in fake_table.deleted_keys
    assert {
        "PK": f"USER#{USER_SUB}",
        "SK": "WORKOUT#2025-11-03#W2#SET#1",
    } in fake_table.deleted_keys


def test_delete_workout_and_sets_does_nothing_when_no_items(fake_table):
    """
    If Dynamo returns no items, the method should return quietly
    and not attempt any deletes.
    """
    repo = DynamoWorkoutRepository(table=fake_table)

    workout_id = "NON_EXISTENT"

    fake_table.response = {"Items": []}

    repo.delete_workout_and_sets(USER_SUB, WORKOUT_DATE_W2, workout_id)

    # Query should still be called
    assert fake_table.last_query_kwargs is not None

    # But no deletes should be recorded
    assert fake_table.deleted_keys == []


def test_delete_workout_and_sets_raises_repoerror_on_client_error(failing_delete_table):
    repo = DynamoWorkoutRepository(table=failing_delete_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.delete_workout_and_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to delete workout and sets from database" in str(excinfo.value)
