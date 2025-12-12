import uuid
from datetime import date as DateType
from datetime import datetime, timezone
from typing import Any

import pytest

from app.models.workout import Workout
from app.routes import workout as workout_routes
from app.utils import db


class FakeWorkoutRepo:
    """
    Tiny fake to stand in for DynamoWorkoutRepository in route tests.
    """

    def __init__(self):
        self.user_subs = []
        self.workouts_to_return = []
        self.created_workouts = []

        self.workout_to_return = None
        self.sets_to_return = []

        self.updated_workouts = []

        self.deleted_calls = []

        self.added_sets: list[tuple[str, DateType, str, str, Any]] = []

        self.set_to_return = None
        self.edited_sets: list[tuple[str, DateType, str, int, object]] = []

    def get_all_for_user(self, user_sub: str):
        self.user_subs.append(user_sub)
        return self.workouts_to_return

    def create_workout(self, user_sub: str, data):
        self.user_subs.append(user_sub)

        new_id = str(uuid.uuid4())
        now = datetime(2025, 1, 1, tzinfo=timezone.utc)

        workout = Workout(
            PK=db.build_user_pk(user_sub),
            SK=db.build_workout_sk(data.date, new_id),
            type="workout",
            date=data.date,
            name=data.name,
            created_at=now,
            updated_at=now,
        )

        self.created_workouts.append(workout)
        return workout

    def get_workout_with_sets(self, user_sub, workout_date, workout_id):
        return self.workout_to_return, self.sets_to_return

    def edit_workout(self, workout):
        self.updated_workouts.append(workout)
        return workout

    def delete_workout_and_sets(self, user_sub, workout_date, workout_id):
        self.deleted_calls.append((user_sub, workout_date, workout_id))

    def add_set(self, user_sub, workout_date, workout_id, exercise_id, form):
        self.added_sets.append((user_sub, workout_date, workout_id, exercise_id, form))
        self.user_subs.append(user_sub)

    def delete_set(self, user_sub, workout_date, workout_id, set_number):
        self.deleted_calls.append((user_sub, workout_date, workout_id, set_number))

    def get_set(self, user_sub, workout_date, workout_id, set_number):
        return self.set_to_return

    def edit_set(self, user_sub, workout_date, workout_id, set_number, form):
        self.edited_sets.append((user_sub, workout_date, workout_id, set_number, form))


@pytest.fixture
def fake_workout_repo(app_instance):
    """
    Override get_workout_repo() for the duration of a test.
    """
    repo = FakeWorkoutRepo()
    app_instance.dependency_overrides[workout_routes.get_workout_repo] = lambda: repo
    try:
        yield repo
    finally:
        app_instance.dependency_overrides.pop(workout_routes.get_workout_repo, None)


class FakeExerciseRepo:
    """
    Tiny fake to stand in for DynamoExerciseRepository in route tests.
    """

    def __init__(self):
        self.calls = []

    def get_exercise_by_id(self, user_sub: str, exercise_id: str):
        # record calls so tests *could* assert on them later
        self.calls.append((user_sub, exercise_id))

        # Return a super simple fake object that behaves enough like an exercise
        class FakeExercise:
            def __init__(self, exercise_id: str):
                self.exercise_id = exercise_id
                self.name = f"Exercise {exercise_id}"

        return FakeExercise(exercise_id)


@pytest.fixture(autouse=True)
def fake_exercise_repo(app_instance):
    """
    Override get_exercise_repo() for all tests that use the FastAPI app.
    """
    repo = FakeExerciseRepo()
    app_instance.dependency_overrides[workout_routes.get_exercise_repo] = lambda: repo
    try:
        yield repo
    finally:
        app_instance.dependency_overrides.pop(workout_routes.get_exercise_repo, None)


@pytest.fixture
def repo_raises(monkeypatch):
    """
    Patch a repo method to raise an exception when called.

    Usage:
        repo_raises(fake_workout_repo, "delete_set", WorkoutRepoError("kaboom"))
    """

    def _apply(repo, method_name: str, exc: Exception):
        def _broken(*args, **kwargs):
            raise exc

        monkeypatch.setattr(repo, method_name, _broken, raising=True)

    return _apply
