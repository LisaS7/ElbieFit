"""
Tests for DynamoWorkoutRepository.get_all_workout_data_for_user.
"""
import pytest

from app.models.workout import Workout, WorkoutSet
from app.repositories.errors import WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import db
from tests.test_data import (
    TEST_DATE_1,
    TEST_DATE_2,
    TEST_WORKOUT_ID_1,
    TEST_WORKOUT_ID_2,
    TEST_WORKOUT_SK_1,
    TEST_WORKOUT_SK_2,
    USER_SUB,
)


# ──────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def workout_w1(workout_factory):
    return workout_factory(
        SK=TEST_WORKOUT_SK_1,
        date=TEST_DATE_1,
        name="Older Workout",
    )


@pytest.fixture
def workout_w2(workout_factory):
    return workout_factory(
        SK=TEST_WORKOUT_SK_2,
        date=TEST_DATE_2,
        name="Newer Workout",
    )


@pytest.fixture
def set_w2_1(set_factory):
    return set_factory(
        SK=db.build_set_sk(TEST_DATE_2, TEST_WORKOUT_ID_2, 1),
        exercise_id="squat",
        set_number=1,
    )


@pytest.fixture
def set_w2_2(set_factory):
    return set_factory(
        SK=db.build_set_sk(TEST_DATE_2, TEST_WORKOUT_ID_2, 2),
        exercise_id="bench",
        set_number=2,
    )


# ──────────────────────────── Tests ────────────────────────────


def test_get_all_workout_data_returns_workouts_and_sets(
    fake_table, workout_w1, workout_w2, set_w2_1, set_w2_2
):
    fake_table.response = {
        "Items": [
            workout_w1.to_ddb_item(),
            workout_w2.to_ddb_item(),
            set_w2_1.to_ddb_item(),
            set_w2_2.to_ddb_item(),
        ]
    }
    repo = DynamoWorkoutRepository(table=fake_table)

    workouts, sets = repo.get_all_workout_data_for_user(USER_SUB)

    assert len(workouts) == 2
    assert all(isinstance(w, Workout) for w in workouts)
    assert len(sets) == 2
    assert all(isinstance(s, WorkoutSet) for s in sets)


def test_get_all_workout_data_workouts_sorted_descending(
    fake_table, workout_w1, workout_w2
):
    fake_table.response = {
        "Items": [
            workout_w1.to_ddb_item(),
            workout_w2.to_ddb_item(),
        ]
    }
    repo = DynamoWorkoutRepository(table=fake_table)

    workouts, _ = repo.get_all_workout_data_for_user(USER_SUB)

    assert workouts[0].date == TEST_DATE_2
    assert workouts[1].date == TEST_DATE_1


def test_get_all_workout_data_empty_returns_empty_lists(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoWorkoutRepository(table=fake_table)

    workouts, sets = repo.get_all_workout_data_for_user(USER_SUB)

    assert workouts == []
    assert sets == []


def test_get_all_workout_data_no_sets_returns_empty_sets_list(fake_table, workout_w1):
    fake_table.response = {"Items": [workout_w1.to_ddb_item()]}
    repo = DynamoWorkoutRepository(table=fake_table)

    workouts, sets = repo.get_all_workout_data_for_user(USER_SUB)

    assert len(workouts) == 1
    assert sets == []


def test_get_all_workout_data_raises_repoerror_on_query_failure(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_workout_data_for_user(USER_SUB)

    assert "Failed to fetch workout data from database" in str(excinfo.value)


def test_get_all_workout_data_raises_repoerror_on_parse_failure(
    fake_table, workout_w1, monkeypatch
):
    fake_table.response = {"Items": [workout_w1.to_ddb_item()]}
    repo = DynamoWorkoutRepository(table=fake_table)

    def boom(_item):
        raise RuntimeError("unexpected parse error")

    monkeypatch.setattr(repo, "_to_model", boom)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.get_all_workout_data_for_user(USER_SUB)

    assert "Failed to parse workout data from database response" in str(excinfo.value)
