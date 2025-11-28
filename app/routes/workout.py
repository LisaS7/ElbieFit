import uuid
from datetime import date
from typing import Annotated, List

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.models.workout import Workout, WorkoutSet
from app.repositories.workout import DynamoWorkoutRepository, WorkoutRepository
from app.templates.templates import templates
from app.utils import auth, dates
from app.utils.log import logger

router = APIRouter(prefix="/workout", tags=["workout"])


def get_workout_repo() -> WorkoutRepository:  # pragma: no cover
    """Fetch the workout repo"""
    return DynamoWorkoutRepository()


def get_sorted_sets_and_defaults(
    sets: List[WorkoutSet],
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
    except Exception:
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
    date: Annotated[date, Form()],
    name: Annotated[str, Form()],
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]
    new_id = uuid.uuid4()

    workout = Workout(
        PK=f"USER#{user_sub}",
        SK=f"WORKOUT#{date.isoformat()}#{new_id}",
        type="workout",
        date=date,
        name=name,
        created_at=dates.now(),
        updated_at=dates.now(),
    )

    workout = repo.create_workout(workout)

    return RedirectResponse(
        url=f"/workout/{date.isoformat()}/{new_id}", status_code=303
    )


# ---------------------- Detail ---------------------------


@router.get("/{workout_date}/{workout_id}")
def view_workout(
    request: Request,
    workout_date: date,
    workout_id: str,
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workout not found")

    sets, defaults = get_sorted_sets_and_defaults(sets)

    return templates.TemplateResponse(
        request,
        "workouts/workout_detail.html",
        {"workout": workout, "sets": sets, "defaults": defaults},
    )


# ---------------------- Edit ---------------------------


@router.get("/{workout_date}/{workout_id}/edit-meta")
def edit_workout_meta(
    request: Request,
    workout_date: date,
    workout_id: str,
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]
    workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)

    return templates.TemplateResponse(
        request, "workouts/edit_meta_form.html", {"workout": workout}
    )


@router.post("/{workout_date}/{workout_id}/meta")
def update_workout_meta(
    request: Request,
    workout_date: date,
    workout_id: str,
    tags: str = Form(""),
    notes: str = Form(""),
    claims=Depends(auth.require_auth),
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    user_sub = claims["sub"]

    try:
        workout, sets = repo.get_workout_with_sets(user_sub, workout_date, workout_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workout not found")

    # parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    workout.tags = tag_list or None

    workout.notes = notes or None
    workout.updated_at = dates.now()

    repo.update_workout(workout)
    sets, defaults = get_sorted_sets_and_defaults(sets)

    return templates.TemplateResponse(
        request,
        "workouts/workout_detail.html",
        {"workout": workout, "sets": sets, "defaults": defaults},
    )
