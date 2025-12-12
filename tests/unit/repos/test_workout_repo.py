import uuid
from datetime import datetime, timezone

import pytest

from app.models.workout import (
    Workout,
    WorkoutCreate,
    WorkoutSet,
)
from app.repositories import workout as workout_repo_module
from app.repositories.errors import WorkoutNotFoundError, WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import dates, db
from tests.test_data import (
    TEST_DATE_1,
    TEST_DATE_2,
    TEST_DATE_3,
    TEST_WORKOUT_ID_2,
    TEST_WORKOUT_SK_1,
    TEST_WORKOUT_SK_2,
    USER_PK,
    USER_SUB,
)

# ──────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def workout_w2(workout_factory):
    return workout_factory(
        SK=TEST_WORKOUT_SK_2,
        date=TEST_DATE_2,
        name="Workout A",
        tags=["upper"],
        notes="Newer",
    )


@pytest.fixture
def workout_w1(workout_factory):
    return workout_factory(
        SK=TEST_WORKOUT_SK_1,
        date=TEST_DATE_1,
        name="Workout B",
        tags=["legs"],
        notes="Older",
    )


@pytest.fixture
def set_w2_1(set_factory):
    # IMPORTANT: ensure SK matches the workout/date/id we’re testing against
    return set_factory(
        PK=USER_PK,
        SK=db.build_set_sk(TEST_DATE_2, TEST_WORKOUT_ID_2, 1),
        exercise_id="squat",
        set_number=1,
    )


@pytest.fixture
def fake_table_response_all(workout_w2, workout_w1, set_w2_1):
    # Includes both workouts + a set item (repo should filter sets out in get_all_for_user)
    return {
        "Items": [
            workout_w2.to_ddb_item(),
            workout_w1.to_ddb_item(),
            set_w2_1.to_ddb_item(),
        ]
    }


@pytest.fixture
def fake_table_response_w2_only(workout_w2, set_w2_1):
    return {"Items": [workout_w2.to_ddb_item(), set_w2_1.to_ddb_item()]}


# ──────────────────────────── get_all_for_user ────────────────────────────


def test_get_all_for_user_returns_sorted_workouts_only(
    fake_table, fake_table_response_all
):
    fake_table.response = fake_table_response_all
    repo = DynamoWorkoutRepository(table=fake_table)

    workouts = repo.get_all_for_user(USER_SUB)

    assert len(workouts) == 2
    assert workouts[0].date == TEST_DATE_2
    assert workouts[1].date == TEST_DATE_1
    assert not any(w.type == "set" for w in workouts)
    assert fake_table.last_query_kwargs is not None


def test_get_all_for_user_empty_results_returns_empty_list(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoWorkoutRepository(table=fake_table)

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
    fake_table, fake_table_response_all, monkeypatch
):
    fake_table.response = fake_table_response_all
    repo = DynamoWorkoutRepository(table=fake_table)

    def boom(_item):
        raise RuntimeError("some totally unexpected error")

    monkeypatch.setattr(repo, "_to_model", boom)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_for_user(USER_SUB)

    assert "Failed to parse workouts from database response" in str(excinfo.value)


# ──────────────────────────── get_workout_with_sets ────────────────────────────


def test_get_workout_with_sets_returns_workout_and_sets(
    fake_table, fake_table_response_all
):
    fake_table.response = fake_table_response_all
    repo = DynamoWorkoutRepository(table=fake_table)

    workout, sets = repo.get_workout_with_sets(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert isinstance(workout, Workout)
    assert workout.PK == USER_PK
    assert workout.SK == TEST_WORKOUT_SK_2
    assert workout.name == "Workout A"
    assert workout.date == TEST_DATE_2

    assert len(sets) == 1
    assert all(isinstance(s, WorkoutSet) for s in sets)
    assert sets[0].exercise_id == "squat"

    assert fake_table.last_query_kwargs is not None


def test_get_workout_with_sets_raises_error_when_not_found(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoWorkoutRepository(table=fake_table)

    with pytest.raises(WorkoutNotFoundError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, TEST_DATE_2, "DOES_NOT_EXIST")

    assert "not found" in str(excinfo.value)


def test_get_workout_with_sets_raises_repoerror_on_client_error(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert "Failed to query workout and sets from database" in str(excinfo.value)


def test_get_workout_with_sets_raises_repoerror_on_parse_error(bad_items_table):
    repo = DynamoWorkoutRepository(table=bad_items_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert "Failed to create workout model from item" in str(excinfo.value)


def test_get_workout_with_sets_wraps_unexpected_exception_in_workoutrepoerror(
    fake_table, fake_table_response_w2_only, monkeypatch
):
    fake_table.response = fake_table_response_w2_only
    repo = DynamoWorkoutRepository(table=fake_table)

    def boom(_item):
        raise RuntimeError("some totally unexpected error")

    monkeypatch.setattr(repo, "_to_model", boom)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_workout_with_sets(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert "Failed to parse workout and sets from response" in str(excinfo.value)


# ──────────────────────────── create_workout ────────────────────────────


def test_create_workout_does_put_item_and_returns_workout(fake_table, monkeypatch):
    fixed_uuid = "12345678-1234-5678-1234-567812345678"
    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    # Patch uuid4 and now for determinism

    monkeypatch.setattr(
        workout_repo_module.uuid, "uuid4", lambda: uuid.UUID(fixed_uuid)
    )
    monkeypatch.setattr(workout_repo_module.dates, "now", lambda: fixed_now)

    repo = DynamoWorkoutRepository(table=fake_table)

    data = WorkoutCreate(date=TEST_DATE_3, name="Bench Party")
    workout = repo.create_workout(user_sub=USER_SUB, data=data)

    assert workout.PK == db.build_user_pk(USER_SUB)
    assert workout.SK == db.build_workout_sk(TEST_DATE_3, fixed_uuid)
    assert workout.type == "workout"
    assert workout.date == TEST_DATE_3
    assert workout.name == "Bench Party"
    assert workout.created_at == fixed_now
    assert workout.updated_at == fixed_now

    assert fake_table.last_put_kwargs == {"Item": workout.to_ddb_item()}


def test_create_workout_raises_repoerror_on_client_error(failing_put_table):
    repo = DynamoWorkoutRepository(table=failing_put_table)

    data = WorkoutCreate(date=TEST_DATE_3, name="Boom Day")

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.create_workout(USER_SUB, data)

    assert "Failed to create workout in database" in str(excinfo.value)


# ──────────────────────────── edit_workout ────────────────────────────


def test_edit_workout_does_put_item_and_returns_workout(fake_table, workout_factory):
    repo = DynamoWorkoutRepository(table=fake_table)

    workout = workout_factory(
        SK=TEST_WORKOUT_SK_2,
        date=TEST_DATE_2,
        name="Updated Lizard Leg Day",
        tags=["legs", "updated"],
        notes="Now with extra squats",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    expected_item = workout.to_ddb_item()
    returned = repo.edit_workout(workout)

    assert returned is workout
    assert fake_table.last_put_kwargs == {"Item": expected_item}


def test_edit_workout_raises_repoerror_on_client_error(
    failing_put_table, workout_factory
):
    repo = DynamoWorkoutRepository(table=failing_put_table)

    workout = workout_factory(
        SK=TEST_WORKOUT_SK_2,
        date=TEST_DATE_2,
        name="Updated",
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.edit_workout(workout)

    assert "Failed to update workout in database" in str(excinfo.value)
