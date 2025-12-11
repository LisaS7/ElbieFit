import uuid
from datetime import datetime, timezone

import pytest

from app.models.workout import Workout
from app.repositories.errors import WorkoutNotFoundError, WorkoutRepoError
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
        self.should_raise_on_get_all = False

        self.workout_to_return = None
        self.sets_to_return = []
        self.should_raise_on_get_one = False
        self.should_raise_repo_error_on_get_one = False

        self.should_raise_on_create = False
        self.updated_workouts = []
        self.should_raise_on_update = False

        self.deleted_calls = []
        self.should_raise_on_delete = False

        self.added_sets: list[tuple[str, str, str, str, dict]] = []
        self.should_raise_on_add_set = False

    # Used by GET /workout/all
    def get_all_for_user(self, user_sub: str):
        self.user_subs.append(user_sub)
        if self.should_raise_on_get_all:
            raise WorkoutRepoError("boom")
        return self.workouts_to_return

    # Used by POST /workout/create
    def create_workout(self, user_sub: str, data):
        if self.should_raise_on_create:
            raise WorkoutRepoError("boom-create")
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

    # Used by GET /workout/{workout_date}/{workout_id}
    def get_workout_with_sets(self, user_sub, workout_date, workout_id):
        if self.should_raise_repo_error_on_get_one:
            raise WorkoutRepoError("boom-get-one")
        if self.should_raise_on_get_one:
            raise WorkoutNotFoundError("Workout not found")
        return self.workout_to_return, self.sets_to_return

    # Used by POST /workout/{workout_date}/{workout_id}/meta
    def edit_workout(self, workout):
        if self.should_raise_on_update:
            raise WorkoutRepoError("boom-update")
        self.updated_workouts.append(workout)
        return workout

    def delete_workout_and_sets(self, user_sub, workout_date, workout_id):
        if self.should_raise_on_delete:
            raise WorkoutRepoError("boom-delete")
        self.deleted_calls.append((user_sub, workout_date, workout_id))

    def add_set(self, user_sub, workout_date, workout_id, exercise_id, form):
        if self.should_raise_on_add_set:
            raise WorkoutRepoError("boom")
        self.added_sets.append((user_sub, workout_date, workout_id, exercise_id, form))
        self.user_subs.append(user_sub)

    def delete_set(self, user_sub, workout_date, workout_id, set_number):
        if self.should_raise_on_delete:
            raise WorkoutRepoError("boom-delete-set")
        self.deleted_calls.append((user_sub, workout_date, workout_id, set_number))


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
