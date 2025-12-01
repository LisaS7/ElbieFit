import pytest

from app.models.exercise import Exercise
from app.repositories.errors import ExerciseRepoError, RepoError
from app.repositories.exercise import DynamoExerciseRepository

USER_SUB = "abc-123"


fake_exercise_table_response = {
    "Items": [
        {
            "PK": f"USER#{USER_SUB}",
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
        },
        {
            "PK": f"USER#{USER_SUB}",
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
        },
    ]
}

# --------------- Get All ---------------


def test_get_all_for_user(fake_table):
    fake_table.response = fake_exercise_table_response
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


def test_get_all_for_user_raises_error(fake_table, monkeypatch):
    repo = DynamoExerciseRepository(table=fake_table)

    def boom(*args, **kwargs):
        raise RepoError("boom in query")

    # Patch the repo's _safe_query, not the table
    monkeypatch.setattr(repo, "_safe_query", boom)

    with pytest.raises(ExerciseRepoError):
        repo.get_all_for_user(USER_SUB)


# --------------- get_exercise_by_id ---------------


def test_get_exercise_by_id_returns_exercise(fake_table):
    fake_table.response = {"Item": fake_exercise_table_response["Items"][0]}

    repo = DynamoExerciseRepository(table=fake_table)

    result = repo.get_exercise_by_id(USER_SUB, "squat")

    assert isinstance(result, Exercise)
    assert result.name == "Back Squat"

    assert fake_table.last_get_kwargs is not None
    assert fake_table.last_get_kwargs["Key"]["PK"] == f"USER#{USER_SUB}"
    assert fake_table.last_get_kwargs["Key"]["SK"] == "EXERCISE#squat"


def test_get_exercise_by_id_not_found_returns_none(fake_table):
    # No "Item" in response → _safe_get returns None → repo should return None
    fake_table.response = {}
    repo = DynamoExerciseRepository(table=fake_table)

    result = repo.get_exercise_by_id(USER_SUB, "does_not_exist")

    assert result is None


def test_get_exercise_by_id_wraps_repo_error(fake_table, monkeypatch):
    repo = DynamoExerciseRepository(table=fake_table)

    def boom(*args, **kwargs):
        raise RepoError("boom in get")

    monkeypatch.setattr(repo, "_safe_get", boom)

    with pytest.raises(ExerciseRepoError) as excinfo:
        repo.get_exercise_by_id(USER_SUB, "squat")

    assert "Failed to get exercise by id for user" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, RepoError)
