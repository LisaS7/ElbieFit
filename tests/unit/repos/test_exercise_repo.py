from app.models.exercise import Exercise
from app.repositories.exercise import DynamoExerciseRepository

user_sub = "abc-123"


fake_exercise_table_response = {
    "Items": [
        {
            "PK": f"USER#{user_sub}",
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
            "PK": f"USER#{user_sub}",
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

    exercises = repo.get_all_for_user(user_sub)

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

    exercises = repo.get_all_for_user(user_sub)

    assert exercises == []
