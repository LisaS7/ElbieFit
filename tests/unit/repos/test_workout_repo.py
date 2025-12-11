import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.workout import (
    Workout,
    WorkoutCreate,
    WorkoutSet,
    WorkoutSetCreate,
    WorkoutSetUpdate,
)
from app.repositories import workout as workout_repo_module
from app.repositories.errors import RepoError, WorkoutNotFoundError, WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import dates, db

USER_SUB = "abc-123"
WORKOUT_DATE_W2 = date(2025, 11, 3)
WORKOUT_ID_W2 = "W2"
WORKOUT_DATE_NEW = date(2025, 11, 16)
SET_NUMBER = 1

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


# --------------- Next set number ---------------
def test_get_next_set_number_returns_1_when_no_sets(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert result == 1
    assert fake_table.last_query_kwargs is not None
    assert "KeyConditionExpression" in fake_table.last_query_kwargs


def test_get_next_set_number_returns_max_plus_one(fake_table):
    """
    When there are existing sets, it should return max(set_number) + 1.
    """
    pk = db.build_user_pk(USER_SUB)
    base_sk = db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2) + "#SET#"

    items = {
        "Items": [
            {"PK": pk, "SK": base_sk + "001"},  # set 1
            {"PK": pk, "SK": base_sk + "003"},  # set 3
            {"PK": pk, "SK": base_sk + "002"},  # set 2
        ]
    }

    fake_table.response = items
    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    # max is 3 -> next should be 4
    assert result == 4


def test_get_next_set_number_ignores_malformed_set_sks(fake_table):
    """
    Malformed SKs that don't end in an int should be ignored. The method should
    still return max(valid_set_number) + 1, or 1 if none are valid.
    """
    pk = db.build_user_pk(USER_SUB)
    base_sk = db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2) + "#SET#"

    fake_table.response = {
        "Items": [
            {"PK": pk, "SK": base_sk + "not-an-int"},
            {"PK": pk, "SK": base_sk + "005"},
        ]
    }

    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    # Only "005" is valid -> max is 5, next is 6
    assert result == 6


def test_get_next_set_number_raises_workoutrepoerror_on_safe_query_failure(
    fake_table, monkeypatch
):
    repo = DynamoWorkoutRepository(table=fake_table)

    def boom(**kwargs):
        raise RepoError("kaboom")

    # Force _safe_query to blow up
    monkeypatch.setattr(repo, "_safe_query", boom)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo._get_next_set_number(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to determine next set number" in str(excinfo.value)


def test_get_next_set_number_returns_1_when_all_set_sks_are_invalid(fake_table):
    pk = db.build_user_pk(USER_SUB)
    base_sk = db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2)

    fake_table.response = {
        "Items": [
            {"PK": pk, "SK": base_sk + "#SET#x"},
            {"PK": pk, "SK": base_sk + "#SET#notanumber"},
            {"PK": pk, "SK": base_sk + "#SET#00x"},
        ]
    }

    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert result == 1


# --------------- Build moved workouts & sets ---------------


def test_build_moved_workout_updates_keys_and_date(fake_table, monkeypatch):
    from app.repositories import workout as workout_repo_module

    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(table=fake_table)

    original = Workout(
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

    new_workout = repo._build_moved_workout(USER_SUB, original, WORKOUT_DATE_NEW)

    assert new_workout.PK == db.build_user_pk(USER_SUB)
    assert new_workout.SK == db.build_workout_sk(WORKOUT_DATE_NEW, WORKOUT_ID_W2)
    assert new_workout.date == WORKOUT_DATE_NEW
    assert new_workout.updated_at == fixed_now  # from patched dates.now
    # sanity: name and created_at carried over
    assert new_workout.name == original.name
    assert new_workout.created_at == original.created_at


def test_build_moved_sets_updates_pk_sk_and_timestamp(fake_table, monkeypatch):
    from app.repositories import workout as workout_repo_module

    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(table=fake_table)

    new_workout = Workout(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_workout_sk(WORKOUT_DATE_NEW, WORKOUT_ID_W2),
        type="workout",
        date=WORKOUT_DATE_NEW,
        name="Moved",
        created_at=fixed_now,
        updated_at=fixed_now,
    )

    original_set = WorkoutSet(
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

    new_sets = repo._build_moved_sets(
        USER_SUB, new_workout, WORKOUT_ID_W2, [original_set]
    )

    assert len(new_sets) == 1
    moved = new_sets[0]

    assert moved.PK == db.build_user_pk(USER_SUB)
    assert moved.SK == db.build_set_sk(WORKOUT_DATE_NEW, WORKOUT_ID_W2, 1)
    assert moved.updated_at == fixed_now  # patched dates.now
    # still the same set content
    assert moved.exercise_id == original_set.exercise_id
    assert moved.reps == original_set.reps
    assert moved.weight_kg == original_set.weight_kg


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

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_for_user(USER_SUB)

    assert "Failed to fetch workouts from database" in str(excinfo.value)


def test_get_all_for_user_raises_repoerror_on_parse_error(bad_items_table):
    repo = DynamoWorkoutRepository(table=bad_items_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_for_user(USER_SUB)

    assert "Failed to create workout model from item" in str(excinfo.value)


def test_get_all_for_user_wraps_unexpected_exception_in_workoutrepoerror(
    fake_table, monkeypatch
):
    # Return at least one valid-looking item so we get as far as _to_model
    fake_table.response = FAKE_TABLE_RESPONSE_ALL
    repo = DynamoWorkoutRepository(table=fake_table)

    # Force an unexpected exception inside the try-block
    def boom(_item):
        raise RuntimeError("some totally unexpected error")

    # Monkeypatch the instance method so the list comprehension explodes
    monkeypatch.setattr(repo, "_to_model", boom)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_for_user(USER_SUB)

    # Check that it hit the generic "parse" handler
    assert "Failed to parse workouts from database response" in str(excinfo.value)


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

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to query workout and sets from database" in str(excinfo.value)


def test_get_workout_with_sets_raises_repoerror_on_parse_error(bad_items_table):
    repo = DynamoWorkoutRepository(table=bad_items_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to create workout model from item" in str(excinfo.value)


def test_get_workout_with_sets_wraps_unexpected_exception_in_workoutrepoerror(
    fake_table, monkeypatch
):
    # Make the query succeed and return normal-looking items
    fake_table.response = FAKE_TABLE_RESPONSE_W2_ONLY
    repo = DynamoWorkoutRepository(table=fake_table)

    # Force an unexpected exception during model conversion
    def boom(_item):
        raise RuntimeError("some totally unexpected error")

    monkeypatch.setattr(repo, "_to_model", boom)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to parse workout and sets from response" in str(excinfo.value)


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


# --- Sets ---


def test_add_set_creates_set_and_writes_to_dynamo(fake_table, monkeypatch):

    repo = DynamoWorkoutRepository(table=fake_table)

    # Make _get_next_set_number see an existing set #1 so it picks #2
    pk = db.build_user_pk(USER_SUB)
    base_sk = db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2) + "#SET#"
    fake_table.response = {
        "Items": [
            {"PK": pk, "SK": base_sk + "001"},
        ]
    }

    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    data = WorkoutSetCreate(
        reps=8,
        weight_kg=Decimal("60.5"),
        rpe=7,
    )

    new_set = repo.add_set(
        user_sub=USER_SUB,
        workout_date=WORKOUT_DATE_W2,
        workout_id=WORKOUT_ID_W2,
        exercise_id="squat",
        data=data,
    )

    # Check model fields
    assert isinstance(new_set, WorkoutSet)
    assert new_set.PK == db.build_user_pk(USER_SUB)
    assert new_set.set_number == 2  # existing set #1 -> next is #2
    assert new_set.exercise_id == "squat"
    assert new_set.reps == 8
    assert new_set.weight_kg == Decimal("60.5")
    assert new_set.rpe == 7
    assert new_set.created_at == fixed_now
    assert new_set.updated_at == fixed_now

    # Check what was written to Dynamo
    assert fake_table.last_put_kwargs == {"Item": new_set.to_ddb_item()}


def test_add_set_raises_workoutrepoerror_on_put_failure(failing_put_table, monkeypatch):
    repo = DynamoWorkoutRepository(table=failing_put_table)

    # Avoid hitting query() on failing_put_table by bypassing _get_next_set_number internals
    monkeypatch.setattr(repo, "_get_next_set_number", lambda *args, **kwargs: 1)

    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    data = WorkoutSetCreate(
        reps=8,
        weight_kg=None,
        rpe=None,
    )

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.add_set(
            user_sub=USER_SUB,
            workout_date=WORKOUT_DATE_W2,
            workout_id=WORKOUT_ID_W2,
            exercise_id="deadlift",
            data=data,
        )

    assert "Failed to add workout set to database" in str(excinfo.value)


# --------------- Edit (No New SK) ---------------


def test_edit_workout_does_put_item_and_returns_workout(fake_table):
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
    returned_item = repo.edit_workout(workout)

    assert fake_table.last_put_kwargs == {"Item": expected_item}
    assert returned_item is workout


def test_edit_workout_raises_repoerror_on_client_error(failing_put_table):
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
        repo.edit_workout(workout)

    assert "Failed to update workout in database" in str(excinfo.value)


# --------------- Edit (New SK) ---------------
def test_move_workout_date_moves_workout_without_sets(fake_table, monkeypatch):
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
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    delete_calls = {}

    def fake_delete(user_sub, workout_date, workout_id):
        delete_calls["user_sub"] = user_sub
        delete_calls["date"] = workout_date
        delete_calls["workout_id"] = workout_id

    monkeypatch.setattr(repo, "delete_workout_and_sets", fake_delete)

    repo.move_workout_date(
        user_sub=USER_SUB,
        workout=workout,
        new_date=WORKOUT_DATE_NEW,
        sets=[],
    )

    assert delete_calls == {
        "user_sub": USER_SUB,
        "date": WORKOUT_DATE_W2,
        "workout_id": WORKOUT_ID_W2,
    }

    assert fake_table.last_put_kwargs is not None
    item = fake_table.last_put_kwargs["Item"]

    assert item["PK"] == db.build_user_pk(USER_SUB)
    assert item["SK"] == db.build_workout_sk(WORKOUT_DATE_NEW, WORKOUT_ID_W2)


def test_move_workout_date_raises_workoutrepoerror_when_write_fails(
    failing_put_table,
):
    repo = DynamoWorkoutRepository(table=failing_put_table)

    # Original workout on old date
    workout = Workout(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2),
        type="workout",
        date=WORKOUT_DATE_W2,
        name="Move Me Dino Day",
        tags=["upper"],
        notes="Roar",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    # No sets needed – we just need the FIRST _safe_put to blow up
    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.move_workout_date(
            user_sub=USER_SUB,
            workout=workout,
            new_date=WORKOUT_DATE_NEW,
            sets=[],
        )

    assert "Failed to write new workout or sets" in str(excinfo.value)


def test_move_workout_date_raises_workoutrepoerror_when_delete_fails(
    fake_table, monkeypatch
):
    """
    If the new workout (and sets) are written successfully but deleting the old
    workout fails, move_workout_date should raise a WorkoutRepoError with the
    expected message.
    """
    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    # Ensure deterministic timestamps
    monkeypatch.setattr(dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(table=fake_table)

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

    # Make delete_workout_and_sets raise after new workout is created
    def fake_delete(user_sub, workout_date, workout_id):
        raise WorkoutRepoError("failed to delete old workout")

    monkeypatch.setattr(repo, "delete_workout_and_sets", fake_delete)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.move_workout_date(
            user_sub=USER_SUB,
            workout=workout,
            new_date=WORKOUT_DATE_NEW,
            sets=[],
        )

    assert "New workout created but failed to delete old one" in str(excinfo.value)


def test_move_workout_date_calls_safe_put_for_sets(fake_table, monkeypatch):
    repo = DynamoWorkoutRepository(table=fake_table)

    workout = Workout(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_workout_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2),
        type="workout",
        date=WORKOUT_DATE_W2,
        name="Move Me Dino Day",
        tags=["upper"],
        notes="Roar",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    set1 = WorkoutSet(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_set_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2, 1),
        type="set",
        exercise_id="squat",
        set_number=1,
        reps=8,
        weight_kg=Decimal("60"),
        rpe=7,
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    calls: list[dict] = []

    def fake_safe_put(item: dict) -> None:
        calls.append(item)

    monkeypatch.setattr(repo, "_safe_put", fake_safe_put)

    repo.move_workout_date(
        user_sub=USER_SUB,
        workout=workout,
        new_date=WORKOUT_DATE_NEW,
        sets=[set1],
    )

    assert len(calls) == 2


# --- Edit set ---


def test_edit_set_updates_fields(fake_table, monkeypatch):
    repo = DynamoWorkoutRepository(table=fake_table)

    def fake_get(**kwargs):
        return WORKOUT_W2_SET1_ITEM.copy()

    monkeypatch.setattr(repo, "_safe_get", fake_get)

    captured: dict = {}

    def fake_put(item: dict) -> None:
        captured["item"] = item

    monkeypatch.setattr(repo, "_safe_put", fake_put)

    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    data = WorkoutSetUpdate(
        reps=10,
        weight_kg=Decimal("75.5"),
        rpe=9,
    )

    repo.edit_set(
        USER_SUB,
        WORKOUT_DATE_W2,
        WORKOUT_ID_W2,
        SET_NUMBER,
        data,
    )

    assert "item" in captured
    item = captured["item"]

    assert item["PK"] == WORKOUT_W2_SET1_ITEM["PK"]
    assert item["SK"] == WORKOUT_W2_SET1_ITEM["SK"]
    assert item["type"] == "set"
    assert item["exercise_id"] == WORKOUT_W2_SET1_ITEM["exercise_id"]
    assert item["set_number"] == WORKOUT_W2_SET1_ITEM["set_number"]
    assert item["created_at"] == WORKOUT_W2_SET1_ITEM["created_at"]

    assert item["reps"] == 10
    assert item["weight_kg"] == Decimal("75.5")
    assert item["rpe"] == 9

    assert item["updated_at"] == dates.dt_to_iso(fixed_now)


def test_edit_set_raises_workoutrepoerror_on_put_failure(fake_table, monkeypatch):
    repo = DynamoWorkoutRepository(table=fake_table)

    monkeypatch.setattr(repo, "_safe_get", lambda **kwargs: WORKOUT_W2_SET1_ITEM.copy())

    def boom(_item: dict) -> None:
        raise RepoError("kaboom")

    monkeypatch.setattr(repo, "_safe_put", boom)

    data = WorkoutSetUpdate(
        reps=8,
        weight_kg=Decimal("60"),
        rpe=7,
    )

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.edit_set(
            USER_SUB,
            WORKOUT_DATE_W2,
            WORKOUT_ID_W2,
            SET_NUMBER,
            data,
        )

    assert "Failed to update set" in str(excinfo.value)


def test_edit_set_raises_workoutnotfound_when_set_missing(fake_table, monkeypatch):
    repo = DynamoWorkoutRepository(table=fake_table)

    # _safe_get returns nothing -> set doesn't exist
    monkeypatch.setattr(repo, "_safe_get", lambda **kwargs: None)

    data = WorkoutSetUpdate(
        reps=8,
        weight_kg=Decimal("60"),
        rpe=7,
    )

    with pytest.raises(WorkoutNotFoundError) as excinfo:
        repo.edit_set(
            USER_SUB,
            WORKOUT_DATE_W2,
            WORKOUT_ID_W2,
            SET_NUMBER,
            data,
        )

    assert "Set 1 not found" in str(excinfo.value)


# --------------- Delete ---------------

# --- Workout ---


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

    assert "Failed to load workout and sets for deletion" in str(excinfo.value)


def test_delete_workout_and_sets_wraps_unexpected_exception_in_workoutrepoerror(
    fake_table, monkeypatch
):
    """
    If Dynamo's batch_writer.delete_item raises an unexpected exception, the
    repository should wrap it in a WorkoutRepoError with the expected message.
    """
    repo = DynamoWorkoutRepository(table=fake_table)

    # Ensure there are items to delete
    fake_table.response = FAKE_TABLE_RESPONSE_W2_ONLY

    class BadBatch:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def delete_item(self, Key):
            raise RuntimeError("boom delete")

    # Replace the table's batch_writer with one that raises on delete
    monkeypatch.setattr(repo._table, "batch_writer", lambda: BadBatch())

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.delete_workout_and_sets(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2)

    assert "Failed to delete workout and sets from database" in str(excinfo.value)


# --- Set ---


def test_delete_set_successful(fake_table):
    repo = DynamoWorkoutRepository(table=fake_table)
    repo.delete_set(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2, SET_NUMBER)

    expected_key = {
        "PK": db.build_user_pk(USER_SUB),
        "SK": db.build_set_sk(WORKOUT_DATE_W2, WORKOUT_ID_W2, SET_NUMBER),
    }

    assert fake_table.deleted_keys == [expected_key]


def test_delete_set_raises_workoutrepoerror_on_dynamo_failure(failing_delete_table):
    repo = DynamoWorkoutRepository(table=failing_delete_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.delete_set(USER_SUB, WORKOUT_DATE_W2, WORKOUT_ID_W2, SET_NUMBER)

    assert "Failed to delete workout set from database" in str(excinfo.value)
