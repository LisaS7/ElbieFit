from datetime import date
from decimal import Decimal

from app.routes import workout as workout_routes
from tests.test_data import (
    TEST_CREATED_DATETIME,
    TEST_DATE_2,
    TEST_UPDATED_DATETIME,
    TEST_WORKOUT_ID_2,
)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def post_set(
    client,
    workout_date: date = TEST_DATE_2,
    workout_id: str = TEST_WORKOUT_ID_2,
    exercise_id: str = "EX-1",
    **overrides,
):
    data = {
        "reps": "8",
        "weight_kg": "60.5",
        "rpe": "9",
    }
    data.update(overrides)

    url = f"/workout/{workout_date.isoformat()}/{workout_id}/set/add?exercise_id={exercise_id}"
    return client.post(url, data=data, follow_redirects=False)


def post_meta(client, workout_date: date, workout_id: str, **overrides):
    data = {
        "name": "Edit Me",
        "date": workout_date.isoformat(),
        "tags": "",
        "notes": "",
    }
    data.update(overrides)

    return client.post(
        f"/workout/{workout_date.isoformat()}/{workout_id}/meta", data=data
    )


def post_edit_set(
    client,
    workout_date: date = TEST_DATE_2,
    workout_id: str = TEST_WORKOUT_ID_2,
    set_number: int = 1,
    **overrides,
):
    data = {
        "reps": "10",
        "weight_kg": "70.5",
        "rpe": "8",
    }
    data.update(overrides)

    url = f"/workout/{workout_date.isoformat()}/{workout_id}/set/{set_number}"
    return client.post(url, data=data, follow_redirects=False)


def assert_html(response):
    assert response.status_code == 200
    assert "<html" in response.text


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────


# ───────────────────────── GET /workout/all ─────────────────────────


def test_get_all_workouts_success_renders_template(
    authenticated_client, fake_workout_repo
):
    fake_workout_repo.workouts_to_return = []
    response = authenticated_client.get("/workout/all")

    assert_html(response)
    assert fake_workout_repo.user_subs == ["test-user-sub"]


def test_get_all_workouts_handles_repo_error(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo, "get_all_for_user", workout_routes.WorkoutRepoError("boom")
    )
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
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}/set/form?exercise_id=EX-1"
    )

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'name="reps"' in response.text
    assert "EX-1" in response.text


# ──────────────────────────── POST /workout/create ────────────────────────────


def test_create_workout_creates_item_and_redirects(
    authenticated_client, fake_workout_repo
):

    response = authenticated_client.post(
        "/workout/create",
        data={"date": TEST_DATE_2.isoformat(), "name": "Bench Party"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert len(fake_workout_repo.created_workouts) == 1

    created = fake_workout_repo.created_workouts[0]
    assert created.date == TEST_DATE_2
    assert created.name == "Bench Party"
    assert fake_workout_repo.user_subs == ["test-user-sub"]

    expected_location = f"/workout/{created.date.isoformat()}/{created.workout_id}"
    assert response.headers["location"] == expected_location


def test_create_workout_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo,
        "create_workout",
        workout_routes.WorkoutRepoError("boom-create"),
    )

    response = authenticated_client.post(
        "/workout/create",
        data={"date": TEST_DATE_2.isoformat(), "name": "Broken Bench"},
        follow_redirects=False,
    )

    assert response.status_code == 500


# ───────────────────── POST /workout/{date}/{id}/set/add ─────────────────────


def test_create_workout_set_adds_set_and_returns_204(
    authenticated_client, fake_workout_repo
):
    response = post_set(authenticated_client, exercise_id="EX-BENCH")

    assert response.status_code == 204
    assert response.headers.get("HX-Trigger") == "workoutSetChanged"

    assert len(fake_workout_repo.added_sets) == 1
    user_sub, w_date, w_id, exercise_id, form = fake_workout_repo.added_sets[0]

    assert user_sub == "test-user-sub"
    assert w_date == TEST_DATE_2
    assert w_id == TEST_WORKOUT_ID_2
    assert exercise_id == "EX-BENCH"

    assert form.reps == 8
    assert form.weight_kg == Decimal("60.5")
    assert form.rpe == 9


def test_create_workout_set_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo, "add_set", workout_routes.WorkoutRepoError("boom-add-set")
    )

    response = post_set(authenticated_client)

    assert response.status_code == 500


# ──────────────────────────── GET /workout/{date}/{id} ────────────────────────────


def test_view_workout_renders_template(
    authenticated_client, fake_workout_repo, workout_factory, set_factory
):

    fake_workout_repo.workout_to_return = workout_factory(
        date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2
    )
    fake_workout_repo.sets_to_return = [
        set_factory(
            workout_date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2, set_number=1
        ),
        set_factory(
            workout_date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2, set_number=2
        ),
    ]

    response = authenticated_client.get(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}"
    )

    assert_html(response)


def test_view_workout_returns_404_when_not_found(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo,
        "get_workout_with_sets",
        workout_routes.WorkoutNotFoundError("Workout not found"),
    )

    response = authenticated_client.get(f"/workout/{TEST_DATE_2.isoformat()}/NOPE")

    assert response.status_code == 404


def test_view_workout_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo
):
    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}"
    )

    assert response.status_code == 500


def test_view_workout_returns_500_when_exercise_repo_raises(
    authenticated_client, fake_workout_repo, workout_factory, set_factory, app_instance
):
    fake_workout_repo.workout_to_return = workout_factory(
        date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2
    )
    fake_workout_repo.sets_to_return = [
        set_factory(
            workout_date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2, exercise_id="EX-1"
        )
    ]

    class BrokenExerciseRepo:
        def get_exercise_by_id(self, user_sub, exercise_id):
            raise workout_routes.ExerciseRepoError("kaboom")

    app_instance.dependency_overrides[workout_routes.get_exercise_repo] = (
        lambda: BrokenExerciseRepo()
    )
    try:
        response = authenticated_client.get(
            f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}"
        )
        assert response.status_code == 500
    finally:
        app_instance.dependency_overrides.pop(workout_routes.get_exercise_repo, None)


# ──────────────────────────── get_sorted_sets_and_defaults ────────────────────────────


def test_get_sorted_sets_and_defaults_empty_list():
    sorted_sets, defaults = workout_routes.get_sorted_sets_and_defaults([])

    assert sorted_sets == []
    assert defaults == {"exercise": "", "reps": "", "weight": ""}


def test_get_sorted_sets_and_defaults_sorts_and_builds_defaults(set_factory):
    sets = [
        set_factory(
            set_number=5,
            exercise_id="EX-2",
            created_at=TEST_CREATED_DATETIME,
        ),
        set_factory(
            set_number=3,
            exercise_id="EX-1",
            created_at=TEST_UPDATED_DATETIME,
        ),
    ]

    sorted_sets, defaults = workout_routes.get_sorted_sets_and_defaults(sets)

    assert [s.exercise_id for s in sorted_sets] == ["EX-2", "EX-1"]

    assert defaults["exercise"] == "EX-1"
    assert defaults["reps"] == 8
    assert defaults["weight"] == 60


# ───────────────────────── POST /workout/{date}/{id}/meta ─────────────────────────


def test_update_workout_meta_updates_workout_and_renders(
    authenticated_client,
    fake_workout_repo,
    fixed_now,
    workout_factory,
    set_factory,
):

    fake_workout_repo.workout_to_return = workout_factory(
        date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2
    )
    fake_workout_repo.sets_to_return = [
        set_factory(workout_date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2)
    ]

    response = post_meta(
        authenticated_client,
        TEST_DATE_2,
        TEST_WORKOUT_ID_2,
        tags="push, legs, heavy",
        notes="Felt strong",
    )

    assert_html(response)
    assert len(fake_workout_repo.updated_workouts) == 1

    updated = fake_workout_repo.updated_workouts[0]
    assert updated.tags == ["push", "legs", "heavy"]
    assert updated.notes == "Felt strong"
    assert updated.updated_at == fixed_now


def test_update_workout_meta_returns_404_when_not_found(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo,
        "get_workout_with_sets",
        workout_routes.WorkoutNotFoundError("Workout not found"),
    )

    response = post_meta(authenticated_client, TEST_DATE_2, "NOPE")

    assert response.status_code == 404


def test_update_workout_meta_returns_500_when_repo_error_on_fetch(
    authenticated_client, fake_workout_repo
):

    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = post_meta(
        authenticated_client,
        TEST_DATE_2,
        TEST_WORKOUT_ID_2,
    )

    assert response.status_code == 500


def test_update_workout_meta_returns_500_when_update_fails(
    authenticated_client, fake_workout_repo, workout_factory, set_factory, repo_raises
):

    fake_workout_repo.workout_to_return = workout_factory(
        date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2
    )
    fake_workout_repo.sets_to_return = [
        set_factory(workout_date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2)
    ]
    repo_raises(
        fake_workout_repo,
        "edit_workout",
        workout_routes.WorkoutRepoError("boom-update"),
    )

    response = post_meta(authenticated_client, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert response.status_code == 500


def test_update_workout_meta_returns_500_when_move_date_fails(
    authenticated_client, fake_workout_repo, workout_factory, set_factory
):

    fake_workout_repo.workout_to_return = workout_factory(
        date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2
    )
    fake_workout_repo.sets_to_return = [
        set_factory(workout_date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2)
    ]

    new_date = date(2025, 11, 4)

    def broken_move(user_sub, workout, new_date_param, sets):
        raise workout_routes.WorkoutRepoError("kaboom")

    fake_workout_repo.move_workout_date = broken_move

    response = post_meta(
        authenticated_client, TEST_DATE_2, TEST_WORKOUT_ID_2, date=new_date.isoformat()
    )

    assert response.status_code == 500


def test_update_workout_meta_moves_date_and_sets_hx_redirect(
    authenticated_client, fake_workout_repo, workout_factory, set_factory
):

    fake_workout_repo.workout_to_return = workout_factory(
        date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2
    )
    fake_workout_repo.sets_to_return = [
        set_factory(workout_date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2)
    ]
    new_date = date(2025, 11, 4)

    moved_workout = workout_factory(date=new_date, workout_id=TEST_WORKOUT_ID_2)

    def fake_move_workout_date(user_sub, workout, new_date_param, sets):
        assert user_sub == "test-user-sub"
        assert new_date_param == new_date
        return moved_workout

    fake_workout_repo.move_workout_date = fake_move_workout_date

    response = post_meta(
        authenticated_client, TEST_DATE_2, TEST_WORKOUT_ID_2, date=new_date.isoformat()
    )
    expected_url = f"/workout/{new_date.isoformat()}/{TEST_WORKOUT_ID_2}"

    assert response.status_code == 204
    assert response.headers.get("HX-Redirect").endswith(expected_url)


# ──────────────────────────── GET /workout/{date}/{id}/edit-meta ────────────────────────────
def test_edit_workout_meta_renders_form(
    authenticated_client, fake_workout_repo, workout_factory
):

    fake_workout_repo.workout_to_return = workout_factory(
        date=TEST_DATE_2, workout_id=TEST_WORKOUT_ID_2
    )
    fake_workout_repo.sets_to_return = []

    response = authenticated_client.get(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}/edit-meta"
    )

    assert response.status_code == 200
    assert 'name="tags"' in response.text
    assert 'name="notes"' in response.text


def test_edit_workout_meta_returns_404_when_not_found(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo,
        "get_workout_with_sets",
        workout_routes.WorkoutNotFoundError("Workout not found"),
    )

    response = authenticated_client.get(
        f"/workout/{TEST_DATE_2.isoformat()}/NOPE/edit-meta"
    )

    assert response.status_code == 404


def test_edit_workout_meta_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo
):

    fake_workout_repo.should_raise_repo_error_on_get_one = True

    response = authenticated_client.get(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}/edit-meta"
    )

    assert response.status_code == 500


# ──────────────────────────── GET /workout/{date}/{id}/set/{set_number}/edit ────────────────────────────


def test_get_edit_set_form_renders_form(
    authenticated_client, fake_workout_repo, set_factory
):
    fake_set = set_factory(
        workout_date=TEST_DATE_2,
        workout_id=TEST_WORKOUT_ID_2,
        set_number=1,
        reps=10,
        weight_kg=Decimal("70"),
        exercise_id="EX-1",
    )

    def fake_get_set(user_sub, workout_date, workout_id, set_number):
        assert user_sub == "test-user-sub"
        assert workout_date == TEST_DATE_2
        assert workout_id == TEST_WORKOUT_ID_2
        assert set_number == 1
        return fake_set

    fake_workout_repo.get_set = fake_get_set

    response = authenticated_client.get(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}/set/1/edit"
    )

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'name="reps"' in response.text
    assert "Save Set" in response.text
    assert "#edit-set-form-container-1" in response.text


def test_get_edit_set_form_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(fake_workout_repo, "get_set", workout_routes.WorkoutRepoError("kaboom"))

    response = authenticated_client.get(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}/set/1/edit"
    )

    assert response.status_code == 500


# ──────────────────────────── POST /{workout_date}/{workout_id}/set/{set_number} ────────────────────────────


def test_edit_set_updates_and_returns_204(authenticated_client, fake_workout_repo):
    calls: dict = {}

    def fake_edit_set(user_sub, workout_date, workout_id, set_number, form):
        calls["user_sub"] = user_sub
        calls["workout_date"] = workout_date
        calls["workout_id"] = workout_id
        calls["set_number"] = set_number
        calls["form"] = form

    fake_workout_repo.edit_set = fake_edit_set

    response = post_edit_set(authenticated_client)

    assert response.status_code == 204
    assert response.headers.get("HX-Trigger") == "workoutSetChanged"

    assert calls["user_sub"] == "test-user-sub"
    assert calls["workout_date"] == TEST_DATE_2
    assert calls["workout_id"] == TEST_WORKOUT_ID_2
    assert calls["set_number"] == 1

    form = calls["form"]
    assert form.reps == 10
    assert form.weight_kg == Decimal("70.5")
    assert form.rpe == 8


def test_edit_set_returns_404_when_set_not_found(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo,
        "edit_set",
        workout_routes.WorkoutNotFoundError("nope"),
    )

    response = post_edit_set(authenticated_client)

    assert response.status_code == 404
    assert "Set not found" in response.text


def test_edit_set_returns_500_when_repo_error(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo,
        "edit_set",
        workout_routes.WorkoutRepoError("kaboom"),
    )

    response = post_edit_set(authenticated_client)

    assert response.status_code == 500
    assert "Error updating set" in response.text


# ──────────────────────────── DELETE /workout/{date}/{id} ────────────────────────────


def test_delete_workout_deletes_and_redirects(authenticated_client, fake_workout_repo):

    response = authenticated_client.delete(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/workout/all"
    assert fake_workout_repo.deleted_calls == [
        ("test-user-sub", TEST_DATE_2, TEST_WORKOUT_ID_2)
    ]


def test_delete_workout_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo, repo_raises
):

    repo_raises(
        fake_workout_repo,
        "delete_workout_and_sets",
        workout_routes.WorkoutRepoError("boom-delete"),
    )

    response = authenticated_client.delete(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}",
        follow_redirects=False,
    )

    assert response.status_code == 500


# ──────────────────────────── DELETE /workout/{date}/{id}/set/{set_number} ────────────────────────────


def test_delete_set_deletes_and_returns_204(authenticated_client, fake_workout_repo):
    response = authenticated_client.delete(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}/set/1",
        follow_redirects=False,
    )

    assert response.status_code == 204
    assert response.headers.get("HX-Trigger") == "workoutSetChanged"


def test_delete_set_returns_500_when_repo_raises(
    authenticated_client, fake_workout_repo, repo_raises
):
    repo_raises(
        fake_workout_repo, "delete_set", workout_routes.WorkoutRepoError("kaboom")
    )

    response = authenticated_client.delete(
        f"/workout/{TEST_DATE_2.isoformat()}/{TEST_WORKOUT_ID_2}/set/1",
        follow_redirects=False,
    )

    assert response.status_code == 500
    assert "Error deleting set" in response.text
