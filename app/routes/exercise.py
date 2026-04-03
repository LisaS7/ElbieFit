from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.models.exercise import ExerciseCreate, ExerciseUpdate
from app.repositories.errors import ExerciseRepoError
from app.repositories.exercise import DynamoExerciseRepository
from app.templates.templates import render_template
from app.utils import auth, dates
from app.utils.log import logger
from app.utils.taxonomy import EQUIPMENT_TYPES, EXERCISE_CATEGORIES, MUSCLE_GROUPS

router = APIRouter(prefix="/exercise", tags=["exercise"])


def get_exercise_repo() -> DynamoExerciseRepository:  # pragma: no cover
    """Fetch the exercise repo"""
    return DynamoExerciseRepository()


def _form_context(exercise=None, action_url="", submit_label="Save", cancel_target="") -> dict:
    return {
        "exercise": exercise,
        "action_url": action_url,
        "submit_label": submit_label,
        "cancel_target": cancel_target,
        "equipment_types": EQUIPMENT_TYPES,
        "exercise_categories": EXERCISE_CATEGORIES,
        "muscle_groups": MUSCLE_GROUPS,
    }


# ---------------------- List all ---------------------------


@router.get("/all")
def get_all_exercises(
    request: Request,
    claims=Depends(auth.require_auth),
    repo: DynamoExerciseRepository = Depends(get_exercise_repo),
):
    """Get all exercises for the current authenticated user"""
    user_sub = claims["sub"]
    logger.info(f"Fetching exercises for user {user_sub}")

    try:
        exercises = repo.get_all_for_user(user_sub)
    except ExerciseRepoError:
        logger.exception(f"Error fetching exercises for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching exercises")
    return render_template(
        request,
        "exercises/exercises.html",
        context={"exercises": exercises},
        status_code=200,
    )


# ---------------------- Create ---------------------------


@router.get("/new-form")
def get_new_exercise_form(
    request: Request,
    claims=Depends(auth.require_auth),
):
    return render_template(
        request,
        "exercises/_exercise_form.html",
        context=_form_context(
            exercise=None,
            action_url=str(request.url_for("create_exercise")),
            submit_label="Create",
            cancel_target="#new-exercise-form-container",
        ),
    )


@router.post("/create")
def create_exercise(
    request: Request,
    form: Annotated[ExerciseCreate, Depends(ExerciseCreate.as_form)],
    claims=Depends(auth.require_auth),
    repo: DynamoExerciseRepository = Depends(get_exercise_repo),
):
    user_sub = claims["sub"]

    try:
        repo.create_exercise(user_sub, form)
    except ExerciseRepoError:
        logger.exception(f"Error creating exercise for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error creating exercise")

    return Response(status_code=204, headers={"HX-Redirect": "/exercise/all"})


# ---------------------- Edit ---------------------------


@router.get("/{exercise_id}/edit")
def get_edit_exercise_form(
    request: Request,
    exercise_id: str,
    claims=Depends(auth.require_auth),
    repo: DynamoExerciseRepository = Depends(get_exercise_repo),
):
    user_sub = claims["sub"]

    try:
        exercise = repo.get_exercise_by_id(user_sub, exercise_id)
    except ExerciseRepoError:
        logger.exception(f"Error fetching exercise {exercise_id} for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching exercise")

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    return render_template(
        request,
        "exercises/_exercise_form.html",
        context=_form_context(
            exercise=exercise,
            action_url=str(request.url_for("update_exercise", exercise_id=exercise_id)),
            submit_label="Save",
            cancel_target=f"#edit-exercise-form-container-{exercise_id}",
        ),
    )


@router.post("/{exercise_id}")
def update_exercise(
    request: Request,
    exercise_id: str,
    form: Annotated[ExerciseUpdate, Depends(ExerciseUpdate.as_form)],
    claims=Depends(auth.require_auth),
    repo: DynamoExerciseRepository = Depends(get_exercise_repo),
):
    user_sub = claims["sub"]

    try:
        exercise = repo.get_exercise_by_id(user_sub, exercise_id)
    except ExerciseRepoError:
        logger.exception(f"Error fetching exercise {exercise_id} for update, user {user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching exercise")

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    exercise.name = form.name
    exercise.equipment = form.equipment
    exercise.category = form.category
    exercise.muscles = form.muscles
    exercise.updated_at = dates.now()

    try:
        repo.update_exercise(exercise)
    except ExerciseRepoError:
        logger.exception(f"Error updating exercise {exercise_id} for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error updating exercise")

    return Response(status_code=204, headers={"HX-Redirect": "/exercise/all"})


# ---------------------- Delete ---------------------------


@router.delete("/{exercise_id}")
def delete_exercise(
    exercise_id: str,
    claims=Depends(auth.require_auth),
    repo: DynamoExerciseRepository = Depends(get_exercise_repo),
):
    user_sub = claims["sub"]

    try:
        repo.delete_exercise(user_sub, exercise_id)
    except ExerciseRepoError:
        logger.exception(f"Error deleting exercise {exercise_id} for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error deleting exercise")

    return Response(status_code=200, content="")
