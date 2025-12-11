from datetime import date, datetime, timezone
from decimal import Decimal

from app.main import app
from app.routes import workout as workout_routes

WORKOUT_DATE = date(2025, 11, 3)
WORKOUT_ID = "W2"


class DummyWorkout:
    def __init__(
        self,
        name="Edit Me",
        date=None,
        tags=None,
        notes=None,
        updated_at=None,
        workout_id=WORKOUT_ID,
    ):
        self.name = name
        self.date = date or WORKOUT_DATE
        self.tags = tags
        self.notes = notes
        self.updated_at = updated_at
        self._workout_id = workout_id

    @property
    def workout_id(self):
        return self._workout_id


class DummySet:
    def __init__(
        self,
        exercise_id="EX-1",
        reps=8,
        weight_kg=60,
        created_at=None,
        set_number=1,
    ):
        self.exercise_id = exercise_id
        self.reps = reps
        self.weight_kg = weight_kg
        self.created_at = created_at or datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.set_number = set_number


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


# ──────────────────────────── GET/workout/new-form ────────────────────────────


def test_get_new_form_renders_form(client):
    response = client.get("/workout/new-form")
    assert response.status_code == 200
    assert 'name="name"' in response.text


# ──────────────────────────── GET /workout/{date}/{id}/set/form ────────────────────────────


def test_get_new_set_form_renders_form(client):
    response = client.get(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}/set/form?exercise_id=EX-1"
    )

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'name="reps"' in response.text
    assert "EX-1" in response.text


# ──────────────────────────── POST /workout/create ────────────────────────────


def test_create_workout_creates_item_and_redirects(
    authenticated_client, fake_workout_repo
):
    workout_date = date(2025, 11, 16)

    response = authenticated_client.post(
        "/workout/create",
        data={"date": workout_date.isoformat(), "name": "Bench Party"},
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert len(fake_workout_repo.created_workouts) == 1
    created = fake_workout_repo.created_workouts[0]

    assert created.date == workout_date
    assert created.name == "Bench Party"
    assert fake_workout_repo.user_subs == ["test-user-sub"]

    expected_location = f"/workout/{created.date.isoformat()}/{created.workout_id}"
    assert response.headers["location"] == expected_location


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


# ───────────────────── POST /workout/{date}/{id}/set/add ─────────────────────


def post_set(
    client,
    workout_date=WORKOUT_DATE,
    workout_id=WORKOUT_ID,
    exercise_id="EX-1",
    **overrides,
):
    data = {
        "reps": "8",
        "weight_kg": "60.5",
        "rpe": "9",
    }
    data.update(overrides)

    url = f"/workout/{workout_date.isoformat()}/{workout_id}/set/add?exercise_id={exercise_id}"

    return client.post(
        url,
        data=data,
        follow_redirects=False,
    )


def test_create_workout_set_adds_set_and_returns_204(
    authenticated_client, fake_workout_repo
):
    response = post_set(authenticated_client, exercise_id="EX-BENCH")

    assert response.status_code == 204
    assert response.headers.get("HX-Trigger") == "workoutSetChanged"

    assert len(fake_workout_repo.added_sets) == 1
    user_sub, w_date, w_id, exercise_id, form = fake_workout_repo.added_sets[0]

    assert user_sub == "test-user-sub"
    assert w_date == WORKOUT_DATE
    assert w_id == WORKOUT_ID
    assert form.reps == 8
    assert form.weight_kg == Decimal("60.5")
    assert form.rpe == 9


def test_create_workout_set_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo
):
    fake_workout_repo.should_raise_on_add_set = True

    response = post_set(authenticated_client)

    assert response.status_code == 500


# ──────────────────────────── GET /workout/{date}/{id} ────────────────────────────


def test_view_workout_renders_template(authenticated_client, fake_workout_repo):

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet(set_number=1), DummySet(set_number=2)]

    response = authenticated_client.get(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}"
    )

    assert response.status_code == 200
    assert "<html" in response.text


def test_view_workout_returns_404_when_not_found(
    authenticated_client, fake_workout_repo
):
    workout_id = "NOPE"

    fake_workout_repo.should_raise_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{WORKOUT_DATE.isoformat()}/{workout_id}"
    )

    assert response.status_code == 404


def test_view_workout_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo
):
    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}"
    )

    assert response.status_code == 500


def test_view_workout_returns_500_when_exercise_repo_raises(
    authenticated_client, fake_workout_repo
):
    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet(exercise_id="EX-1")]

    class BrokenExerciseRepo:
        def get_exercise_by_id(self, user_sub, exercise_id):
            raise workout_routes.ExerciseRepoError("kaboom")

    app.dependency_overrides[workout_routes.get_exercise_repo] = (
        lambda: BrokenExerciseRepo()
    )

    try:
        response = authenticated_client.get(
            f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}"
        )

        assert response.status_code == 500

    finally:
        app.dependency_overrides.pop(workout_routes.get_exercise_repo, None)


# ──────────────────────────── POST /workout/{date}/{id}/meta ────────────────────────────


def post_meta(client, workout_date, workout_id, **overrides):
    data = {
        "name": "Edit Me",
        "date": workout_date.isoformat(),
        "tags": "",
        "notes": "",
    }
    data.update(overrides)

    return client.post(
        f"/workout/{workout_date.isoformat()}/{workout_id}/meta",
        data=data,
    )


def test_get_sorted_sets_and_defaults_empty_list():
    sorted_sets, defaults = workout_routes.get_sorted_sets_and_defaults([])

    assert sorted_sets == []
    assert defaults == {"exercise": "", "reps": "", "weight": ""}


def test_get_sorted_sets_and_defaults_sorts_and_builds_defaults():
    sets = [
        DummySet(
            set_number=5,
            exercise_id="EX-2",
            created_at=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
        ),
        DummySet(
            set_number=3,
            exercise_id="EX-1",
            created_at=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
        ),
    ]

    # ok to ignore type error - DummySet behaves like a WorkoutSet here
    sorted_sets, defaults = workout_routes.get_sorted_sets_and_defaults(sets)  # type: ignore[arg-type]

    assert [s.exercise_id for s in sorted_sets] == ["EX-1", "EX-2"]

    assert defaults["exercise"] == "EX-2"
    assert defaults["reps"] == 8
    assert defaults["weight"] == 60


def test_update_workout_meta_updates_workout_and_renders(
    authenticated_client, fake_workout_repo, monkeypatch
):

    fixed_now = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_routes.dates, "now", lambda: fixed_now)

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet()]

    response = post_meta(
        authenticated_client,
        WORKOUT_DATE,
        WORKOUT_ID,
        tags="push, legs, heavy",
        notes="Felt strong",
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
    workout_id = "NOPE"

    fake_workout_repo.should_raise_on_get_one = True

    response = post_meta(authenticated_client, WORKOUT_DATE, workout_id)

    assert response.status_code == 404


def test_update_workout_meta_returns_500_when_repo_error_on_fetch(
    authenticated_client, fake_workout_repo
):

    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = post_meta(
        authenticated_client,
        WORKOUT_DATE,
        WORKOUT_ID,
    )

    assert response.status_code == 500


def test_update_workout_meta_returns_500_when_update_fails(
    authenticated_client, fake_workout_repo, monkeypatch
):

    fixed_now = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_routes.dates, "now", lambda: fixed_now)

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet()]
    fake_workout_repo.should_raise_on_update = True

    response = post_meta(authenticated_client, WORKOUT_DATE, WORKOUT_ID)

    assert response.status_code == 500


def test_update_workout_meta_returns_500_when_move_date_fails(
    authenticated_client, fake_workout_repo, monkeypatch
):

    fixed_now = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_routes.dates, "now", lambda: fixed_now)

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet()]

    new_date = date(2025, 11, 4)

    def broken_move(user_sub, workout, new_date_param, sets):
        raise workout_routes.WorkoutRepoError("kaboom")

    fake_workout_repo.move_workout_date = broken_move

    response = post_meta(authenticated_client, new_date, WORKOUT_ID)

    assert response.status_code == 500


def test_update_workout_meta_moves_date_and_sets_hx_redirect(
    authenticated_client, fake_workout_repo, monkeypatch
):
    fixed_now = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(workout_routes.dates, "now", lambda: fixed_now)

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = [DummySet()]
    new_date = date(2025, 11, 4)

    class MovedWorkout:
        def __init__(self, date, workout_id):
            self.date = date
            self._workout_id = workout_id

        @property
        def workout_id(self):
            return self._workout_id

    moved_workout = MovedWorkout(new_date, WORKOUT_ID)

    def fake_move_workout_date(user_sub, workout, new_date_param, sets):
        assert user_sub == "test-user-sub"
        assert new_date_param == new_date
        return moved_workout

    fake_workout_repo.move_workout_date = fake_move_workout_date

    response = post_meta(authenticated_client, new_date, WORKOUT_ID)
    expected_url = f"/workout/{new_date.isoformat()}/{WORKOUT_ID}"

    assert response.status_code == 204
    assert response.headers.get("HX-Redirect").endswith(expected_url)


# ──────────────────────────── GET /workout/{date}/{id}/edit-meta ────────────────────────────
def test_edit_workout_meta_renders_form(authenticated_client, fake_workout_repo):

    fake_workout_repo.workout_to_return = DummyWorkout()
    fake_workout_repo.sets_to_return = []

    response = authenticated_client.get(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}/edit-meta"
    )

    assert response.status_code == 200
    # sanity check that we're actually seeing the edit form
    assert 'name="tags"' in response.text
    assert 'name="notes"' in response.text


def test_edit_workout_meta_returns_404_when_not_found(
    authenticated_client, fake_workout_repo
):
    workout_id = "NOPE"

    fake_workout_repo.should_raise_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{WORKOUT_DATE.isoformat()}/{workout_id}/edit-meta"
    )

    assert response.status_code == 404


def test_edit_workout_meta_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo
):

    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}/edit-meta"
    )

    assert response.status_code == 500


# ──────────────────────────── DELETE /workout/{date}/{id} ────────────────────────────


def test_delete_workout_deletes_and_redirects(authenticated_client, fake_workout_repo):

    response = authenticated_client.delete(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/workout/all"
    assert fake_workout_repo.deleted_calls == [
        ("test-user-sub", WORKOUT_DATE, WORKOUT_ID)
    ]


def test_delete_workout_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo
):

    fake_workout_repo.should_raise_on_delete = True

    response = authenticated_client.delete(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}",
        follow_redirects=False,
    )

    assert response.status_code == 500


# ──────────────────────────── DELETE /workout/{date}/{id}/set/{set_number} ────────────────────────────


def test_delete_set_deletes_and_returns_204(authenticated_client, fake_workout_repo):
    response = authenticated_client.delete(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}/set/1",
        follow_redirects=False,
    )

    assert response.status_code == 204
    assert response.headers.get("HX-Trigger") == "workoutSetChanged"


def test_delete_set_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo
):
    def broken_delete_set(user_sub, workout_date, workout_id, set_number):
        raise workout_routes.WorkoutRepoError("kaboom")

    fake_workout_repo.delete_set = broken_delete_set

    response = authenticated_client.delete(
        f"/workout/{WORKOUT_DATE.isoformat()}/{WORKOUT_ID}/set/1",
        follow_redirects=False,
    )

    assert response.status_code == 500
    assert "Error deleting set" in response.text
