import uuid
from datetime import date, datetime, timezone

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


# ──────────────────────────── /workout/all ────────────────────────────


def test_get_all_workouts_success_renders_template(
    authenticated_client, fake_workout_repo
):
    fake_workout_repo.workouts_to_return = []
    response = authenticated_client.get("/workout/all")

    assert response.status_code == 200
    assert "<html" in response.text
    assert fake_workout_repo.user_subs == ["test-user-sub"]


def test_get_all_workouts_handles_repo_error(authenticated_client, fake_workout_repo):
    fake_workout_repo.should_raise_on_get_all = True
    response = authenticated_client.get("/workout/all")
    assert response.status_code == 500


# ──────────────────────────── /workout/new-form ────────────────────────────


def test_get_new_form_renders_form(client):
    response = client.get("/workout/new-form")
    assert response.status_code == 200
    assert 'name="name"' in response.text


# ──────────────────────────── /workout/create ────────────────────────────


def test_create_workout_creates_item_and_redirects(
    authenticated_client, fake_workout_repo, monkeypatch
):
    fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    fixed_now = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    workout_date = date(2025, 11, 16)

    # Patch uuid.uuid4 used inside app.routes.workout
    monkeypatch.setattr(workout_routes.uuid, "uuid4", lambda: fixed_uuid)
    # Patch dates.now() imported in the workout routes module
    monkeypatch.setattr(workout_routes.dates, "now", lambda: fixed_now)

    response = authenticated_client.post(
        "/workout/create",
        data={"date": workout_date.isoformat(), "name": "Bench Party"},
        follow_redirects=False,
    )

    # Redirect to the edit page for the new workout
    assert response.status_code == 303
    expected_location = f"/workout/{workout_date.isoformat()}/{fixed_uuid}"
    assert response.headers["location"] == expected_location

    # Get the Workout object passed to the repo
    created = fake_workout_repo.created_workouts[0]

    assert created.PK == "USER#test-user-sub"
    assert created.SK == f"WORKOUT#{workout_date.isoformat()}#{fixed_uuid}"
    assert created.type == "workout"
    assert created.name == "Bench Party"
    assert created.date == workout_date
    assert created.created_at == fixed_now
    assert created.updated_at == fixed_now


# ──────────────────────────── /workout/{date}/{id} ────────────────────────────


def test_view_workout_renders_template(authenticated_client, fake_workout_repo):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    class DummyWorkout:
        def __init__(self):
            self.name = "Test Workout"
            self.date = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

    class DummySet:
        def __init__(self, n):
            self.set_number = n
            self.exercise_id = "EX-" + str(n)
            self.reps = 8
            self.weight_kg = 60
            self.created_at = datetime(2025, 1, 1, 12, n, tzinfo=timezone.utc)

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet(1), DummySet(2)]

    response = authenticated_client.get(
        f"/workout/{workout_date.isoformat()}/{workout_id}"
    )

    assert response.status_code == 200
    assert "<html" in response.text


def test_view_workout_returns_404_when_not_found(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 3)
    workout_id = "NOPE"

    fake_workout_repo.should_raise_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{workout_date.isoformat()}/{workout_id}"
    )

    assert response.status_code == 404
