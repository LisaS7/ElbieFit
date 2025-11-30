from datetime import date as DateType
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.models.workout import WorkoutCreate, WorkoutSet, WorkoutUpdate
from app.repositories.errors import WorkoutNotFoundError, WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository, WorkoutRepository
from app.templates.templates import templates
from app.utils import auth, dates
from app.utils.log import logger

router = APIRouter(prefix="/workout", tags=["workout"])


def get_workout_repo() -> WorkoutRepository:  # pragma: no cover
    """Fetch the workout repo"""
    return DynamoWorkoutRepository()


def get_sorted_sets_and_defaults(
    sets: Sequence[WorkoutSet],
) -> tuple[list[WorkoutSet], dict]:
    """
    Return sets sorted by created_at, and the defaults for the "add set" form.
    """

    sorted_sets = sorted(sets, key=lambda s: s.created_at)

    defaults = {"exercise": "", "reps": "", "weight": ""}

    if sorted_sets:
        last = sorted_sets[-1]
        defaults = {
            "exercise": last.exercise_id,
            "reps": last.reps,
            "weight": last.weight_kg,
        }

    return sorted_sets, defaults


# ---------------------- List all ---------------------------


@router.get("/all")
def get_all_workouts(
    request: Request,
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    """Get all workouts for the current authenticated user"""
    user_sub = claims["sub"]

    logger.info(f"Fetching workouts for user {user_sub}")

    try:
        workouts = repo.get_all_for_user(user_sub)
    except WorkoutRepoError:
        logger.exception(f"Error fetching workouts for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching workouts")
    return templates.TemplateResponse(
        request,
        "workouts/workouts.html",
        {"workouts": workouts},
        status_code=200,
    )


# ---------------------- Create ---------------------------


@router.get("/new-form")
def get_new_form(request: Request):
    return templates.TemplateResponse(request, "workouts/new_form.html")


@router.post("/create")
def create_workout(
    request: Request,
    form: Annotated[WorkoutCreate, Depends(WorkoutCreate.as_form)],
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        workout = repo.create_workout(user_sub, data=form)
    except WorkoutRepoError:
        logger.exception("Error creating workout")
        raise HTTPException(status_code=500, detail="Error creating workout")

    return RedirectResponse(
        url=f"/workout/{workout.date.isoformat()}/{workout.workout_id}", status_code=303
    )


# ---------------------- Detail ---------------------------


@router.get("/{workout_date}/{workout_id}")
def view_workout(
    request: Request,
    workout_date: DateType,
    workout_id: str,
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)
    except WorkoutNotFoundError:
        raise HTTPException(status_code=404, detail="Workout not found")
    except WorkoutRepoError:
        logger.exception("Error fetching workout")
        raise HTTPException(status_code=500, detail="Error fetching workout")

    sets, defaults = get_sorted_sets_and_defaults(sets)

    return templates.TemplateResponse(
        request,
        "workouts/workout_detail.html",
        {"workout": workout, "sets": sets, "defaults": defaults},
    )


# ---------------------- Edit ---------------------------


# ---- Return the form -----
@router.get("/{workout_date}/{workout_id}/edit-meta")
def edit_workout_meta(
    request: Request,
    workout_date: DateType,
    workout_id: str,
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)
    except WorkoutNotFoundError:
        raise HTTPException(status_code=404, detail="Workout not found")
    except WorkoutRepoError:
        logger.exception("Error fetching workout for edit")
        raise HTTPException(status_code=500, detail="Error fetching workout")

    return templates.TemplateResponse(
        request, "workouts/edit_meta_form.html", {"workout": workout}
    )


# ---- Make the update -----
@router.post("/{workout_date}/{workout_id}/meta")
def update_workout_meta(
    request: Request,
    workout_date: DateType,
    workout_id: str,
    form: WorkoutUpdate = Depends(WorkoutUpdate.as_form),
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)
    except WorkoutNotFoundError:
        raise HTTPException(status_code=404, detail="Workout not found")
    except WorkoutRepoError:
        logger.exception("Error fetching workout for update")
        raise HTTPException(status_code=500, detail="Error fetching workout")

    old_date = workout.date
    new_date = form.date

    workout.name = form.name
    workout.notes = form.notes or None
    workout.tags = form.tags
    workout.updated_at = dates.now()

    # if date hasn't changed then update existing item
    if new_date == old_date:
        try:
            repo.update_workout(workout)
        except WorkoutRepoError:
            logger.exception("Error updating workout")
            raise HTTPException(status_code=500, detail="Error updating workout")

    # if date has changed then create new and delete old
    else:
        try:
            repo.move_workout_date(user_sub, workout, new_date, sets)
        except WorkoutRepoError:
            logger.exception("Error updating workout with date change")
            raise HTTPException(status_code=500, detail="Error updating workout")

    sets, defaults = get_sorted_sets_and_defaults(sets)

    return templates.TemplateResponse(
        request,
        "workouts/workout_detail.html",
        {"workout": workout, "sets": sets, "defaults": defaults},
    )


# ---------------------- Delete ---------------------------


@router.delete("/{workout_date}/{workout_id}")
def delete_workout(
    workout_date: DateType,
    workout_id: str,
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        repo.delete_workout_and_sets(user_sub, workout_date, workout_id)
    except WorkoutRepoError:
        logger.exception("Error deleting workout")
        raise HTTPException(status_code=500, detail="Error deleting workout")

    return RedirectResponse(url="/workout/all", status_code=303)
