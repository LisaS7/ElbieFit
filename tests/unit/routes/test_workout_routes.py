import uuid
from datetime import date, datetime, timezone

from app.routes import workout as workout_routes

# ──────────────────────────── GET /workout/all ────────────────────────────


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


# ──────────────────────────── POST /workout/create ────────────────────────────


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


def test_create_workout_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 16)

    fake_workout_repo.should_raise_on_create = True

    response = authenticated_client.post(
        "/workout/create",
        data={"date": workout_date.isoformat(), "name": "Broken Bench"},
        follow_redirects=False,
    )

    assert response.status_code == 500


# ──────────────────────────── GET /workout/{date}/{id} ────────────────────────────


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


def test_view_workout_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{workout_date.isoformat()}/{workout_id}"
    )

    assert response.status_code == 500


# ──────────────────────────── POST /workout/{date}/{id}/meta ────────────────────────────


def test_get_sorted_sets_and_defaults_empty_list():
    sorted_sets, defaults = workout_routes.get_sorted_sets_and_defaults([])

    assert sorted_sets == []
    assert defaults == {"exercise": "", "reps": "", "weight": ""}


def test_get_sorted_sets_and_defaults_sorts_and_builds_defaults():
    class DummySet:
        def __init__(self, minute, exercise_id):
            self.exercise_id = exercise_id
            self.reps = 8
            self.weight_kg = 60
            self.created_at = datetime(2025, 1, 1, 12, minute, tzinfo=timezone.utc)

    sets = [DummySet(5, "EX-2"), DummySet(3, "EX-1")]

    # ok to ignore type error - DummySet behaves like a WorkoutSet here
    sorted_sets, defaults = workout_routes.get_sorted_sets_and_defaults(sets)  # type: ignore[arg-type]

    # sorted by created_at
    assert [s.exercise_id for s in sorted_sets] == ["EX-1", "EX-2"]

    # defaults use the last (most recent) set
    assert defaults["exercise"] == "EX-2"
    assert defaults["reps"] == 8
    assert defaults["weight"] == 60


def test_update_workout_meta_updates_workout_and_renders(
    authenticated_client, fake_workout_repo, monkeypatch
):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    fixed_now = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_routes.dates, "now", lambda: fixed_now)

    class DummyWorkout:
        def __init__(self):
            self.name = "Edit Me"
            self.date = workout_date
            self.tags = None
            self.notes = None
            self.updated_at = None

    class DummySet:
        def __init__(self):
            self.exercise_id = "EX-1"
            self.reps = 8
            self.weight_kg = 60
            self.created_at = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet()]

    response = authenticated_client.post(
        f"/workout/{workout_date.isoformat()}/{workout_id}/meta",
        data={
            "name": "Edit Me",  # required now
            "date": workout_date.isoformat(),
            "tags": "push, legs, heavy",
            "notes": "Felt strong",
        },
    )

    assert response.status_code == 200
    assert "<html" in response.text

    # Check workout was updated and passed to repo.update_workout
    assert len(fake_workout_repo.updated_workouts) == 1
    updated = fake_workout_repo.updated_workouts[0]

    assert updated.tags == ["push", "legs", "heavy"]
    assert updated.notes == "Felt strong"
    assert updated.updated_at == fixed_now


def test_update_workout_meta_returns_404_when_not_found(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 3)
    workout_id = "NOPE"

    fake_workout_repo.should_raise_on_get_one = True

    response = authenticated_client.post(
        f"/workout/{workout_date.isoformat()}/{workout_id}/meta",
        data={
            "name": "Does not matter",
            "date": workout_date.isoformat(),
            "tags": "",
            "notes": "",
        },
    )

    assert response.status_code == 404


def test_update_workout_meta_returns_500_when_repo_error_on_fetch(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = authenticated_client.post(
        f"/workout/{workout_date.isoformat()}/{workout_id}/meta",
        data={
            "name": "Does not matter",
            "date": workout_date.isoformat(),
            "tags": "push",
            "notes": "Broken",
        },
    )

    assert response.status_code == 500


def test_update_workout_meta_returns_500_when_update_fails(
    authenticated_client, fake_workout_repo, monkeypatch
):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    fixed_now = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_routes.dates, "now", lambda: fixed_now)

    class DummyWorkout:
        def __init__(self):
            self.name = "Edit Me"
            self.date = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
            self.tags = None
            self.notes = None
            self.updated_at = None

    class DummySet:
        def __init__(self):
            self.exercise_id = "EX-1"
            self.reps = 8
            self.weight_kg = 60
            self.created_at = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet()]
    fake_workout_repo.should_raise_on_update = True

    response = authenticated_client.post(
        f"/workout/{workout_date.isoformat()}/{workout_id}/meta",
        data={
            "name": "Does not matter",
            "date": workout_date.isoformat(),
            "tags": "push, legs",
            "notes": "update fails",
        },
    )

    assert response.status_code == 500


# ──────────────────────────── GET /workout/{date}/{id}/edit-meta ────────────────────────────
def test_edit_workout_meta_renders_form(authenticated_client, fake_workout_repo):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    class DummyWorkout:
        def __init__(self):
            self.name = "Edit Me"
            self.date = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
            self.tags = ["push"]
            self.notes = "Old notes"

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = []

    response = authenticated_client.get(
        f"/workout/{workout_date.isoformat()}/{workout_id}/edit-meta"
    )

    assert response.status_code == 200
    # sanity check that we're actually seeing the edit form
    assert 'name="tags"' in response.text
    assert 'name="notes"' in response.text


def test_edit_workout_meta_returns_404_when_not_found(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 3)
    workout_id = "NOPE"

    fake_workout_repo.should_raise_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{workout_date.isoformat()}/{workout_id}/edit-meta"
    )

    assert response.status_code == 404


def test_edit_workout_meta_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{workout_date.isoformat()}/{workout_id}/edit-meta"
    )

    assert response.status_code == 500


# ──────────────────────────── DELETE /workout/{date}/{id} ────────────────────────────


def test_delete_workout_deletes_and_redirects(authenticated_client, fake_workout_repo):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    response = authenticated_client.delete(
        f"/workout/{workout_date.isoformat()}/{workout_id}",
        follow_redirects=False,
    )

    # route should redirect to /workout/all
    assert response.status_code == 303
    assert response.headers["location"] == "/workout/all"

    # repo method should have been called with correct arguments
    assert fake_workout_repo.deleted_calls == [
        ("test-user-sub", workout_date, workout_id)
    ]


def test_delete_workout_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 3)
    workout_id = "W2"

    fake_workout_repo.should_raise_on_delete = True

    response = authenticated_client.delete(
        f"/workout/{workout_date.isoformat()}/{workout_id}",
        follow_redirects=False,
    )

    assert response.status_code == 500
