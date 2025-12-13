from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.workout import WorkoutSet, WorkoutSetCreate, WorkoutSetUpdate
from app.repositories.errors import RepoError, WorkoutNotFoundError, WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import dates, db
from tests.test_data import (
    TEST_DATE_2,
    TEST_WORKOUT_ID_2,
    USER_PK,
    USER_SUB,
)

# ──────────────────────────── _get_next_set_number ────────────────────────────


def test_get_next_set_number_returns_1_when_no_sets(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert result == 1
    assert fake_table.last_query_kwargs is not None


def test_get_next_set_number_returns_max_plus_one(fake_table):
    base_sk = db.build_workout_sk(TEST_DATE_2, TEST_WORKOUT_ID_2) + "#SET#"

    fake_table.response = {
        "Items": [
            {"PK": USER_PK, "SK": base_sk + "001"},
            {"PK": USER_PK, "SK": base_sk + "003"},
            {"PK": USER_PK, "SK": base_sk + "002"},
        ]
    }

    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert result == 4


def test_get_next_set_number_ignores_malformed_set_sks(fake_table):
    base_sk = db.build_workout_sk(TEST_DATE_2, TEST_WORKOUT_ID_2) + "#SET#"

    fake_table.response = {
        "Items": [
            {"PK": USER_PK, "SK": base_sk + "not-an-int"},
            {"PK": USER_PK, "SK": base_sk + "005"},
        ]
    }

    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert result == 6


def test_get_next_set_number_returns_1_when_all_set_sks_invalid(fake_table):
    base_sk = db.build_workout_sk(TEST_DATE_2, TEST_WORKOUT_ID_2)

    fake_table.response = {
        "Items": [
            {"PK": USER_PK, "SK": base_sk + "#SET#x"},
            {"PK": USER_PK, "SK": base_sk + "#SET#notanumber"},
        ]
    }

    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo._get_next_set_number(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert result == 1


def test_get_next_set_number_wraps_client_error(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo._get_next_set_number(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert "Failed to determine next set number" in str(excinfo.value)


# ──────────────────────────── add_set ────────────────────────────


def test_add_set_creates_set_and_writes_to_dynamo(fake_table, fixed_now):
    repo = DynamoWorkoutRepository(table=fake_table)

    # Existing set #1 → next should be #2
    base_sk = db.build_workout_sk(TEST_DATE_2, TEST_WORKOUT_ID_2) + "#SET#"
    fake_table.response = {"Items": [{"PK": USER_PK, "SK": base_sk + "001"}]}

    data = WorkoutSetCreate(reps=8, weight_kg=Decimal("60.5"), rpe=7)

    new_set = repo.add_set(
        user_sub=USER_SUB,
        workout_date=TEST_DATE_2,
        workout_id=TEST_WORKOUT_ID_2,
        exercise_id="squat",
        data=data,
    )

    assert isinstance(new_set, WorkoutSet)
    assert new_set.set_number == 2
    assert new_set.exercise_id == "squat"
    assert new_set.reps == 8
    assert new_set.weight_kg == Decimal("60.5")
    assert new_set.rpe == 7
    assert new_set.created_at == fixed_now
    assert new_set.updated_at == fixed_now

    assert fake_table.last_put_kwargs == {"Item": new_set.to_ddb_item()}


def test_add_set_wraps_put_failure(failing_put_table, monkeypatch):
    repo = DynamoWorkoutRepository(table=failing_put_table)

    monkeypatch.setattr(repo, "_get_next_set_number", lambda *_, **__: 1)
    monkeypatch.setattr(dates, "now", lambda: datetime.now(timezone.utc))

    data = WorkoutSetCreate(reps=8, weight_kg=None, rpe=None)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.add_set(
            user_sub=USER_SUB,
            workout_date=TEST_DATE_2,
            workout_id=TEST_WORKOUT_ID_2,
            exercise_id="deadlift",
            data=data,
        )

    assert "Failed to add workout set to database" in str(excinfo.value)


# ──────────────────────────── get_set ────────────────────────────


def test_get_set_returns_parsed_workoutset(fake_table, set_factory):
    set_item = set_factory()
    fake_table.response = {"Item": set_item.to_ddb_item()}

    repo = DynamoWorkoutRepository(table=fake_table)

    result = repo.get_set(
        user_sub=USER_SUB,
        workout_date=TEST_DATE_2,
        workout_id=TEST_WORKOUT_ID_2,
        set_number=1,
    )

    assert isinstance(result, WorkoutSet)
    assert result.PK == set_item.PK
    assert result.SK == set_item.SK
    assert result.exercise_id == set_item.exercise_id


def test_get_set_returns_not_found_when_missing(fake_table):
    fake_table.response = {}
    repo = DynamoWorkoutRepository(table=fake_table)

    with pytest.raises(WorkoutNotFoundError):
        repo.get_set(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2, 1)


def test_get_set_wraps_client_error(failing_get_table):
    repo = DynamoWorkoutRepository(table=failing_get_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_set(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2, 1)

    assert "Failed to load set from database" in str(excinfo.value)


def test_get_set_wraps_parse_error(fake_table, set_factory):
    set_item = set_factory()

    bad_item = {
        "PK": set_item.PK,
        "SK": set_item.SK,
        "type": "set",
    }

    fake_table.response = {"Item": bad_item}
    repo = DynamoWorkoutRepository(table=fake_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_set(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2, 1)

    assert "Failed to parse workout set from database" in str(excinfo.value)


# ──────────────────────────── edit_set ────────────────────────────


def test_edit_set_updates_fields(fake_table, set_factory, fixed_now):
    set_item = set_factory()
    fake_table.response = {"Item": set_item.to_ddb_item()}
    repo = DynamoWorkoutRepository(table=fake_table)

    data = WorkoutSetUpdate(reps=10, weight_kg=Decimal("75.5"), rpe=9)

    repo.edit_set(
        USER_SUB,
        TEST_DATE_2,
        TEST_WORKOUT_ID_2,
        set_item.set_number,
        data,
    )

    assert fake_table.last_put_kwargs is not None
    item = fake_table.last_put_kwargs["Item"]

    assert item["PK"] == set_item.PK
    assert item["SK"] == set_item.SK
    assert item["type"] == "set"
    assert item["exercise_id"] == set_item.exercise_id
    assert item["set_number"] == set_item.set_number
    assert item["created_at"] == dates.dt_to_iso(set_item.created_at)

    assert item["reps"] == 10
    assert item["weight_kg"] == Decimal("75.5")
    assert item["rpe"] == 9
    assert item["updated_at"] == dates.dt_to_iso(fixed_now)


def test_edit_set_raises_not_found_when_missing(fake_table):
    fake_table.response = {}
    repo = DynamoWorkoutRepository(table=fake_table)

    data = WorkoutSetUpdate(reps=8, weight_kg=Decimal("60"), rpe=7)

    with pytest.raises(WorkoutNotFoundError):
        repo.edit_set(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2, 1, data)


def test_edit_set_wraps_put_failure(fake_table, set_factory, monkeypatch):
    set_item = set_factory()
    fake_table.response = {"Item": set_item.to_ddb_item()}

    repo = DynamoWorkoutRepository(table=fake_table)

    def boom(_item: dict):
        raise RepoError("kaboom")

    monkeypatch.setattr(repo, "_safe_put", boom)

    data = WorkoutSetUpdate(reps=8, weight_kg=Decimal("60"), rpe=7)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.edit_set(
            USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2, set_item.set_number, data
        )

    assert "Failed to update set" in str(excinfo.value)


# ──────────────────────────── delete_set ────────────────────────────


def test_delete_set_successful(fake_table):
    repo = DynamoWorkoutRepository(table=fake_table)

    repo.delete_set(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2, 1)

    expected_key = {
        "PK": USER_PK,
        "SK": db.build_set_sk(TEST_DATE_2, TEST_WORKOUT_ID_2, 1),
    }

    assert fake_table.deleted_keys == [expected_key]


def test_delete_set_wraps_client_error(failing_delete_table):
    repo = DynamoWorkoutRepository(table=failing_delete_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.delete_set(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2, 1)

    assert "Failed to delete workout set from database" in str(excinfo.value)
