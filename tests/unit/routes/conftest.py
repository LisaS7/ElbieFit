import pytest

from app.repositories.errors import WorkoutNotFoundError, WorkoutRepoError
from app.routes import workout as workout_routes


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

    # Used by GET /workout/all
    def get_all_for_user(self, user_sub: str):
        self.user_subs.append(user_sub)
        if self.should_raise_on_get_all:
            raise WorkoutRepoError("boom")
        return self.workouts_to_return

    # Used by POST /workout/create
    def create_workout(self, workout):
        if self.should_raise_on_create:
            raise WorkoutRepoError("boom-create")
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
    def update_workout(self, workout):
        if self.should_raise_on_update:
            raise WorkoutRepoError("boom-update")
        self.updated_workouts.append(workout)
        return workout

    def delete_workout_and_sets(self, user_sub, workout_date, workout_id):
        if self.should_raise_on_delete:
            raise WorkoutRepoError("boom-delete")
        self.deleted_calls.append((user_sub, workout_date, workout_id))


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
