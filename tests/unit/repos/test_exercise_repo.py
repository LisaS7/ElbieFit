import pytest

from app.models.exercise import Exercise
from app.repositories.errors import ExerciseRepoError
from app.repositories.exercise import DynamoExerciseRepository
from tests.test_data import USER_PK, USER_SUB

FAKE_EXERCISE_1 = {
    "PK": USER_PK,
    "SK": "EXERCISE#squat",
    "type": "exercise",
    "name": "Back Squat",
    "category": "strength",
    "muscles": ["quads", "glutes"],
    "equipment": "barbell",
    "default_sets": 5,
    "default_reps": 5,
    "created_at": "2025-11-03T09:00:00Z",
    "updated_at": "2025-11-03T09:00:00Z",
}
FAKE_EXERCISE_2 = {
    "PK": USER_PK,
    "SK": "EXERCISE#bench_press",
    "type": "exercise",
    "name": "Bench Press",
    "category": "strength",
    "muscles": ["chest", "triceps"],
    "equipment": "barbell",
    "default_sets": 5,
    "default_reps": 5,
    "created_at": "2025-11-03T10:00:00Z",
    "updated_at": "2025-11-03T10:00:00Z",
}


FAKE_EXERCISE_TABLE_RESPONSE = {
    "Items": [
        FAKE_EXERCISE_1,
        FAKE_EXERCISE_2,
    ]
}

# --------------- Get All ---------------


def test_get_all_for_user(fake_table):
    fake_table.response = FAKE_EXERCISE_TABLE_RESPONSE
    repo = DynamoExerciseRepository(table=fake_table)

    exercises = repo.get_all_for_user(USER_SUB)

    assert len(exercises) == 2
    assert all(isinstance(e, Exercise) for e in exercises)

    names = [e.name for e in exercises]
    assert "Back Squat" in names
    assert "Bench Press" in names

    assert fake_table.last_query_kwargs is not None
    assert "KeyConditionExpression" in fake_table.last_query_kwargs


def test_get_all_for_user_empty_results_returns_empty_list(fake_table):
    fake_table.response = {"Items": []}
    repo = DynamoExerciseRepository(table=fake_table)

    exercises = repo.get_all_for_user(USER_SUB)

    assert exercises == []


def test_get_all_for_user_wraps_repo_error(failing_query_table):
    repo = DynamoExerciseRepository(table=failing_query_table)

    with pytest.raises(ExerciseRepoError):
        repo.get_all_for_user(USER_SUB)


# --------------- get_exercise_by_id ---------------


def test_get_exercise_by_id_returns_exercise(fake_table):
    fake_table.response = {"Item": FAKE_EXERCISE_TABLE_RESPONSE["Items"][0]}

    repo = DynamoExerciseRepository(table=fake_table)

    result = repo.get_exercise_by_id(USER_SUB, "squat")

    assert isinstance(result, Exercise)
    assert result.name == "Back Squat"

    assert fake_table.last_get_kwargs == {
        "Key": {"PK": USER_PK, "SK": "EXERCISE#squat"}
    }


def test_get_exercise_by_id_not_found_returns_none(fake_table):
    fake_table.response = {}
    repo = DynamoExerciseRepository(table=fake_table)

    result = repo.get_exercise_by_id(USER_SUB, "does_not_exist")

    assert result is None


def test_get_exercise_by_id_wraps_repo_error(failing_get_table):
    repo = DynamoExerciseRepository(table=failing_get_table)

    with pytest.raises(ExerciseRepoError) as excinfo:
        repo.get_exercise_by_id(USER_SUB, "squat")

    assert "Failed to get exercise by id for user" in str(excinfo.value)
