from fastapi import APIRouter, Depends, HTTPException, Request

from app.repositories.workout import DynamoWorkoutRepository, WorkoutRepository
from app.templates.templates import templates
from app.utils import auth
from app.utils.log import logger

router = APIRouter(prefix="/workout", tags=["workout"])


def get_workout_repo() -> WorkoutRepository:
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
        {"request": request, "workouts": workouts},
        status_code=200,
    )


@router.get("/new-form")
def get_new_form(request: Request):
    return templates.TemplateResponse(request, "workouts/new-form.html")
