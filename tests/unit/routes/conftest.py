import pytest

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
        self.updated_workouts = []

    # Used by GET /workout/all
    def get_all_for_user(self, user_sub: str):
        self.user_subs.append(user_sub)
        if self.should_raise_on_get_all:
            raise RuntimeError("boom")
        return self.workouts_to_return

    # Used by POST /workout/create
    def create_workout(self, workout):
        self.created_workouts.append(workout)
        return workout

    # Used by GET /workout/{workout_date}/{workout_id}
    def get_workout_with_sets(self, user_sub, workout_date, workout_id):
        if self.should_raise_on_get_one:
            raise KeyError("Workout not found")
        return self.workout_to_return, self.sets_to_return

    # Used by POST /workout/{workout_date}/{workout_id}/meta
    def update_workout(self, workout):
        self.updated_workouts.append(workout)
        return workout


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
