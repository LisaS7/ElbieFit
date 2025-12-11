from datetime import date as DateType
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.models.workout import (
    WorkoutCreate,
    WorkoutSet,
    WorkoutSetCreate,
    WorkoutUpdate,
)
from app.repositories.errors import (
    ExerciseRepoError,
    WorkoutNotFoundError,
    WorkoutRepoError,
)
from app.repositories.exercise import DynamoExerciseRepository, ExerciseRepository
from app.repositories.workout import DynamoWorkoutRepository, WorkoutRepository
from app.templates.templates import templates
from app.utils import auth, dates
from app.utils.log import logger

router = APIRouter(prefix="/workout", tags=["workout"])


def get_workout_repo() -> WorkoutRepository:  # pragma: no cover
    """Fetch the workout repo"""
    return DynamoWorkoutRepository()


def get_exercise_repo() -> ExerciseRepository:  # pragma: no cover
    """Fetch the exercise repo"""
    return DynamoExerciseRepository()


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


@router.get("/{workout_date}/{workout_id}/set/form")
def get_new_set_form(
    request: Request, workout_date: DateType, workout_id: str, exercise_id: str
):
    logger.debug(
        f"Getting new set form for workout {workout_id} on {workout_date} for exercise {exercise_id}"
    )
    return templates.TemplateResponse(
        request,
        "workouts/new_set_form.html",
        {
            "workout_date": workout_date,
            "workout_id": workout_id,
            "exercise_id": exercise_id,
        },
    )


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


@router.post("/{workout_date}/{workout_id}/set/add")
def add_set(
    workout_date: DateType,
    workout_id: str,
    exercise_id: str,
    form: Annotated[WorkoutSetCreate, Depends(WorkoutSetCreate.as_form)],
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        repo.add_set(user_sub, workout_date, workout_id, exercise_id, form)
    except WorkoutRepoError:
        logger.exception("Error creating workout set")
        raise HTTPException(status_code=500, detail="Error creating workout set")

    return Response(status_code=204, headers={"HX-Trigger": "workoutSetChanged"})


# ---------------------- Detail ---------------------------


@router.get("/{workout_date}/{workout_id}")
def view_workout(
    request: Request,
    workout_date: DateType,
    workout_id: str,
    claims=Depends(auth.require_auth),
    workout_repo: WorkoutRepository = Depends(get_workout_repo),
    exercise_repo: ExerciseRepository = Depends(get_exercise_repo),
):
    user_sub = claims["sub"]

    # ---- Fetch workout and sets -----
    try:
        workout, sets = workout_repo.get_workout_with_sets(
            user_sub, workout_date, workout_id
        )
    except WorkoutNotFoundError:
        logger.warning(
            "Workout not found",
            extra={
                "user_sub": user_sub,
                "workout_date": workout_date.isoformat(),
                "workout_id": workout_id,
            },
        )
        raise HTTPException(status_code=404, detail="Workout not found")
    except WorkoutRepoError:
        logger.exception(
            "Error fetching workout",
            extra={
                "user_sub": user_sub,
                "workout_date": workout_date.isoformat(),
                "workout_id": workout_id,
            },
        )
        raise HTTPException(status_code=500, detail="Error fetching workout")

    logger.debug(
        "Fetched workout and sets",
        extra={
            "workout_id_attr": getattr(workout, "workout_id", None),
            "sets_count": len(sets),
            "set_numbers": [getattr(s, "set_number", None) for s in sets],
        },
    )

    sets, defaults = get_sorted_sets_and_defaults(sets)

    # ---- Fetch exercise details -----
    exercise_map = {}

    try:
        for s in sets:
            exercise_id = s.exercise_id
            if exercise_id not in exercise_map:
                exercise = exercise_repo.get_exercise_by_id(user_sub, exercise_id)
                if exercise:
                    exercise_map[exercise_id] = exercise
    except ExerciseRepoError:
        logger.exception(
            "Error fetching exercise details",
            extra={
                "user_sub": user_sub,
                "workout_id": workout_id,
            },
        )
        raise HTTPException(status_code=500, detail="Error fetching exercise details")

    # ---- Finish ----
    return templates.TemplateResponse(
        request,
        "workouts/workout_detail.html",
        {
            "workout": workout,
            "sets": sets,
            "defaults": defaults,
            "exercises": exercise_map,
        },
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
        logger.warning(
            "Workout not found for edit",
            extra={
                "user_sub": user_sub,
                "workout_date": workout_date.isoformat(),
                "workout_id": workout_id,
            },
        )
        raise HTTPException(status_code=404, detail="Workout not found")
    except WorkoutRepoError:
        logger.exception(
            "Error fetching workout for edit",
            extra={
                "user_sub": user_sub,
                "workout_id": workout_id,
            },
        )
        raise HTTPException(status_code=500, detail="Error fetching workout")

    logger.debug(f"Loading edit meta form for workout {workout.workout_id}")

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

    logger.info(
        "Updating workout meta",
        extra={
            "user_sub": user_sub,
            "workout_date": workout_date.isoformat(),
            "workout_id": workout_id,
            "form_date": form.date.isoformat() if form.date else None,
        },
    )

    try:
        workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)
    except WorkoutNotFoundError:
        logger.warning(
            "Workout not found for update",
            extra={"user_sub": user_sub, "workout_id": workout_id},
        )
        raise HTTPException(status_code=404, detail="Workout not found")
    except WorkoutRepoError:
        logger.exception(
            "Error fetching workout for update",
            extra={
                "user_sub": user_sub,
                "workout_id": workout_id,
            },
        )
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
            logger.exception(
                "Error updating workout",
                extra={
                    "user_sub": user_sub,
                    "workout_id": workout_id,
                },
            )
            raise HTTPException(status_code=500, detail="Error updating workout")

        sets, defaults = get_sorted_sets_and_defaults(sets)

        logger.debug(f"Updated metadata for workout {workout_id}. No date change.")

        return templates.TemplateResponse(
            request,
            "workouts/workout_detail.html",
            {"workout": workout, "sets": sets, "defaults": defaults},
        )

    # if date has changed then create new and delete old
    else:
        try:
            logger.debug(
                f"Moving workout date from {old_date} to {new_date} for {workout.workout_id}"
            )
            workout = repo.move_workout_date(user_sub, workout, new_date, sets)
        except WorkoutRepoError:
            logger.exception(
                "Error updating workout with date change",
                extra={
                    "user_sub": user_sub,
                    "workout_id": workout_id,
                },
            )
            raise HTTPException(status_code=500, detail="Error updating workout")

        new_url = request.url_for(
            "view_workout",
            workout_date=workout.date,
            workout_id=workout.workout_id,
        )

        logger.info(
            "Workout date changed, issuing HX-Redirect",
            extra={
                "user_sub": user_sub,
                "workout_id": workout_id,
                "redirect_url": new_url,
            },
        )

        return Response(status_code=204, headers={"HX-Redirect": str(new_url)})


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
        logger.debug(f"Deleting workout {workout_id}")
        repo.delete_workout_and_sets(user_sub, workout_date, workout_id)
    except WorkoutRepoError:
        logger.exception(
            "Error deleting workout",
            extra={
                "user_sub": user_sub,
                "workout_id": workout_id,
            },
        )
        raise HTTPException(status_code=500, detail="Error deleting workout")

    return RedirectResponse(url="/workout/all", status_code=303)


@router.delete("/{workout_date}/{workout_id}/set/{set_number}")
def delete_set(
    request: Request,
    workout_date: DateType,
    workout_id: str,
    set_number: int,
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):

    user_sub = claims["sub"]

    try:
        logger.debug(f"Deleting set {set_number} for workout {workout_id}")
        repo.delete_set(user_sub, workout_date, workout_id, set_number)
    except WorkoutRepoError:
        logger.exception(
            f"Error deleting set {set_number} from workout {workout_id}",
            extra={
                "user_sub": user_sub,
                "workout_id": workout_id,
            },
        )
        raise HTTPException(status_code=500, detail="Error deleting set")

    # Fire an event which htmx picks up to reload the page
    return Response(status_code=204, headers={"HX-Trigger": "workoutSetChanged"})
