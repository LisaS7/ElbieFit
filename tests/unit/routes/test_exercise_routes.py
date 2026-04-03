from datetime import datetime, timezone

import pytest

from app.models.exercise import Exercise
from app.repositories.errors import ExerciseRepoError
from app.utils import db

USER_SUB = "test-user-sub"

VALID_FORM = {
    "name": "Barbell Squat",
    "equipment": "barbell",
    "category": "legs",
    "muscles": ["quads", "glutes"],
}


def _make_exercise(exercise_id: str = "e1") -> Exercise:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return Exercise(
        PK=db.build_user_pk(USER_SUB),
        SK=db.build_exercise_sk(exercise_id),
        type="exercise",
        name="Barbell Squat",
        equipment="barbell",
        category="legs",
        muscles=["quads", "glutes"],
        created_at=now,
        updated_at=now,
    )


# ---------------------- GET /exercise/all ---------------------------


def test_get_all_exercises_returns_200(authenticated_client, fake_exercise_route_repo):
    fake_exercise_route_repo.seed(_make_exercise())

    resp = authenticated_client.get("/exercise/all")

    assert resp.status_code == 200
    assert "Barbell Squat" in resp.text


def test_get_all_exercises_empty_shows_message(authenticated_client, fake_exercise_route_repo):
    resp = authenticated_client.get("/exercise/all")

    assert resp.status_code == 200
    assert "No exercises found" in resp.text


def test_get_all_exercises_repo_error_returns_500(
    authenticated_client, fake_exercise_route_repo, repo_raises
):
    repo_raises(fake_exercise_route_repo, "get_all_for_user", ExerciseRepoError("boom"))

    resp = authenticated_client.get("/exercise/all")

    assert resp.status_code == 500


# ---------------------- GET /exercise/new-form ---------------------------


def test_get_new_exercise_form_returns_200(authenticated_client, fake_exercise_route_repo):
    resp = authenticated_client.get("/exercise/new-form")

    assert resp.status_code == 200
    assert "<form" in resp.text
    assert "barbell" in resp.text.lower()


# ---------------------- POST /exercise/create ---------------------------


def test_create_exercise_redirects(authenticated_client, fake_exercise_route_repo):
    resp = authenticated_client.post("/exercise/create", data=VALID_FORM)

    assert resp.status_code == 204
    assert resp.headers.get("HX-Redirect") == "/exercise/all"
    assert len(fake_exercise_route_repo.created) == 1
    assert fake_exercise_route_repo.created[0].name == "Barbell Squat"


def test_create_exercise_repo_error_returns_500(
    authenticated_client, fake_exercise_route_repo
):
    fake_exercise_route_repo.raise_on_create = True

    resp = authenticated_client.post("/exercise/create", data=VALID_FORM)

    assert resp.status_code == 500


def test_create_exercise_invalid_equipment_returns_500(
    authenticated_client, fake_exercise_route_repo
):
    # Validation error from as_form is not auto-converted to 422 by FastAPI;
    # form selects prevent invalid values in normal usage.
    data = {**VALID_FORM, "equipment": "trampoline"}

    resp = authenticated_client.post("/exercise/create", data=data)

    assert resp.status_code == 500


def test_create_exercise_no_muscles_returns_500(
    authenticated_client, fake_exercise_route_repo
):
    # Empty muscles list fails ExerciseFormBase validator → 500 for out-of-band
    # requests; checkboxes prevent this in the normal UI.
    data = {k: v for k, v in VALID_FORM.items() if k != "muscles"}

    resp = authenticated_client.post("/exercise/create", data=data)

    assert resp.status_code == 500


# ---------------------- GET /exercise/{id}/edit ---------------------------


def test_get_edit_form_returns_200_with_exercise_data(
    authenticated_client, fake_exercise_route_repo
):
    exercise = _make_exercise("e1")
    fake_exercise_route_repo.seed(exercise)

    resp = authenticated_client.get("/exercise/e1/edit")

    assert resp.status_code == 200
    assert "Barbell Squat" in resp.text
    assert "<form" in resp.text


def test_get_edit_form_not_found_returns_404(authenticated_client, fake_exercise_route_repo):
    resp = authenticated_client.get("/exercise/missing/edit")

    assert resp.status_code == 404


def test_get_edit_form_repo_error_returns_500(
    authenticated_client, fake_exercise_route_repo
):
    fake_exercise_route_repo.raise_on_get = True

    resp = authenticated_client.get("/exercise/e1/edit")

    assert resp.status_code == 500


# ---------------------- POST /exercise/{id} ---------------------------


def test_update_exercise_redirects(authenticated_client, fake_exercise_route_repo):
    fake_exercise_route_repo.seed(_make_exercise("e1"))

    resp = authenticated_client.post("/exercise/e1", data={**VALID_FORM, "name": "Updated Squat"})

    assert resp.status_code == 204
    assert resp.headers.get("HX-Redirect") == "/exercise/all"
    assert len(fake_exercise_route_repo.updated) == 1
    assert fake_exercise_route_repo.updated[0].name == "Updated Squat"


def test_update_exercise_not_found_returns_404(authenticated_client, fake_exercise_route_repo):
    resp = authenticated_client.post("/exercise/missing", data=VALID_FORM)

    assert resp.status_code == 404


def test_update_exercise_repo_error_on_fetch_returns_500(
    authenticated_client, fake_exercise_route_repo
):
    fake_exercise_route_repo.raise_on_get = True

    resp = authenticated_client.post("/exercise/e1", data=VALID_FORM)

    assert resp.status_code == 500


def test_update_exercise_repo_error_on_save_returns_500(
    authenticated_client, fake_exercise_route_repo
):
    fake_exercise_route_repo.seed(_make_exercise("e1"))
    fake_exercise_route_repo.raise_on_update = True

    resp = authenticated_client.post("/exercise/e1", data=VALID_FORM)

    assert resp.status_code == 500


# ---------------------- DELETE /exercise/{id} ---------------------------


def test_delete_exercise_returns_200_empty(authenticated_client, fake_exercise_route_repo):
    fake_exercise_route_repo.seed(_make_exercise("e1"))

    resp = authenticated_client.delete("/exercise/e1")

    assert resp.status_code == 200
    assert resp.content == b""
    assert ("test-user-sub", "e1") in fake_exercise_route_repo.deleted


def test_delete_exercise_repo_error_returns_500(
    authenticated_client, fake_exercise_route_repo
):
    fake_exercise_route_repo.raise_on_delete = True

    resp = authenticated_client.delete("/exercise/e1")

    assert resp.status_code == 500
