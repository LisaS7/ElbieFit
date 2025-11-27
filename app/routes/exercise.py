from fastapi import APIRouter, Depends, HTTPException, Request

from app.repositories.exercise import DynamoExerciseRepository, ExerciseRepository
from app.templates.templates import templates
from app.utils import auth
from app.utils.log import logger

router = APIRouter(prefix="/exercise", tags=["exercise"])


def get_exercise_repo() -> ExerciseRepository:  # pragma: no cover
    """Fetch the exercise repo"""
    return DynamoExerciseRepository()


@router.get("/all")
def get_all_exercises(
    request: Request,
    claims=Depends(auth.require_auth),
    repo: ExerciseRepository = Depends(get_exercise_repo),
):
    """Get all exercises for the current authenticated user"""
    user_sub = claims["sub"]
    logger.info(f"Fetching exercises for user {user_sub}")

    try:
        exercises = repo.get_all_for_user(user_sub)
    except Exception:
        logger.exception(f"Error fetching workouts for user {user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching workouts")
    return templates.TemplateResponse(
        request, "exercises/exercises.html", {"exercises": exercises}, status_code=200
    )
