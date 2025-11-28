import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.models.workout import Workout
from app.repositories.workout import DynamoWorkoutRepository, WorkoutRepository
from app.templates.templates import templates
from app.utils import auth, dates
from app.utils.log import logger

router = APIRouter(prefix="/workout", tags=["workout"])


def get_workout_repo() -> WorkoutRepository:  # pragma: no cover
    """Fetch the workout repo"""
    return DynamoWorkoutRepository()


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

    sets.sort(key=lambda s: s.created_at)

    defaults = {"exercise": "", "reps": "", "weight": ""}

    if sets:
        last = sets[-1]
        defaults = {
            "exercise": last.exercise_id,
            "reps": last.reps,
            "weight": last.weight_kg,
        }

    return templates.TemplateResponse(
        request,
        "workouts/workout_detail.html",
        {"workout": workout, "sets": sets, "defaults": defaults},
    )
