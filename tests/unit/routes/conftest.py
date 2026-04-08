import pytest

from app.routes import exercise as exercise_routes
from app.routes import profile as profile_routes
from app.routes import workout as workout_routes
from tests.fakes import FakeExerciseRepo, FakeProfileRepo, FakeWorkoutRepo

# ---------------- Workout --------------------


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


# ------------------ Exercise ----------------------


@pytest.fixture(autouse=True)
def fake_exercise_repo(app_instance):
    """
    Override workout_routes.get_exercise_repo() for all tests (autouse).
    """
    repo = FakeExerciseRepo()
    app_instance.dependency_overrides[workout_routes.get_exercise_repo] = lambda: repo
    try:
        yield repo
    finally:
        app_instance.dependency_overrides.pop(workout_routes.get_exercise_repo, None)


@pytest.fixture
def fake_exercise_route_repo(app_instance):
    """
    Override exercise_routes.get_exercise_repo() for exercise route tests.
    """
    repo = FakeExerciseRepo()
    app_instance.dependency_overrides[exercise_routes.get_exercise_repo] = lambda: repo
    try:
        yield repo
    finally:
        app_instance.dependency_overrides.pop(exercise_routes.get_exercise_repo, None)


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


@pytest.fixture
def fake_profile_repo(app_instance):
    """
    Override get_profile_repo() for the duration of a test.
    """
    created = []

    def _make(**kwargs) -> FakeProfileRepo:
        repo = FakeProfileRepo(**kwargs)
        app_instance.dependency_overrides[profile_routes.get_profile_repo] = (
            lambda: repo
        )
        created.append(repo)
        return repo

    try:
        yield _make
    finally:
        app_instance.dependency_overrides.pop(profile_routes.get_profile_repo, None)
