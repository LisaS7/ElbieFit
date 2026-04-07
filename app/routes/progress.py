from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.repositories.errors import WorkoutRepoError
from app.repositories.exercise import DynamoExerciseRepository
from app.repositories.profile import DynamoProfileRepository
from app.repositories.workout import DynamoWorkoutRepository
from app.routes.profile import get_profile_repo
from app.routes.workout import get_exercise_repo, get_workout_repo
from app.templates.templates import render_template
from app.utils import auth, progress
from app.utils.log import logger

router = APIRouter(tags=["progress"])


@router.get("/progress")
def progress_page(
    request: Request,
    claims=Depends(auth.require_auth),
    workout_repo: DynamoWorkoutRepository = Depends(get_workout_repo),
    exercise_repo: DynamoExerciseRepository = Depends(get_exercise_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    user_sub = claims["sub"]

    try:
        workouts, sets = workout_repo.get_all_workout_data_for_user(user_sub)
    except WorkoutRepoError:
        logger.exception(f"Error fetching workouts for progress page user_sub={user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching workouts")

    try:
        exercises = exercise_repo.get_all_for_user(user_sub)
    except Exception:
        logger.exception(f"Error fetching exercises for progress page user_sub={user_sub}")
        raise HTTPException(status_code=500, detail="Error fetching exercises")

    profile = profile_repo.get_for_user(user_sub)
    weight_unit = profile.weight_unit if profile else "kg"

    return render_template(
        request,
        "progress/progress.html",
        context={
            "freq_data": progress.build_frequency_chart_data(workouts),
            "volume_data": progress.build_volume_chart_data(sets, weight_unit),
            "dist_data": progress.build_distribution_chart_data(sets, exercises),
            "exercises": exercises,
        },
    )


@router.get("/progress/volume")
def volume_chart(
    request: Request,
    exercise_id: str = Query(""),
    claims=Depends(auth.require_auth),
    workout_repo: DynamoWorkoutRepository = Depends(get_workout_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    user_sub = claims["sub"]

    try:
        if exercise_id:
            sets = workout_repo.get_sets_for_exercise(exercise_id)
        else:
            _, sets = workout_repo.get_all_workout_data_for_user(user_sub)
    except WorkoutRepoError:
        logger.exception(
            f"Error fetching workout data for volume chart user_sub={user_sub}"
        )
        raise HTTPException(status_code=500, detail="Error fetching workout data")

    profile = profile_repo.get_for_user(user_sub)
    weight_unit = profile.weight_unit if profile else "kg"

    chart_data = progress.build_volume_chart_data(
        sets, weight_unit, exercise_id=exercise_id or None
    )

    return render_template(
        request,
        "progress/_volume_chart.html",
        context={"chart_data": chart_data},
    )


@router.get("/progress/exercise")
def exercise_chart(
    request: Request,
    exercise_id: str = Query(...),
    claims=Depends(auth.require_auth),
    workout_repo: DynamoWorkoutRepository = Depends(get_workout_repo),
    exercise_repo: DynamoExerciseRepository = Depends(get_exercise_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    user_sub = claims["sub"]

    exercise = exercise_repo.get_exercise_by_id(user_sub, exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    try:
        sets = workout_repo.get_sets_for_exercise(exercise_id)
    except WorkoutRepoError:
        logger.exception(
            f"Error fetching workout data for exercise chart user_sub={user_sub}"
        )
        raise HTTPException(status_code=500, detail="Error fetching workout data")

    profile = profile_repo.get_for_user(user_sub)
    weight_unit = profile.weight_unit if profile else "kg"

    chart_data = progress.build_exercise_progress_data(sets, exercise_id, weight_unit)

    return render_template(
        request,
        "progress/_exercise_chart.html",
        context={
            "chart_data": chart_data,
            "exercise_name": exercise.name,
        },
    )


@router.get("/progress/1rm")
def one_rm_chart(
    request: Request,
    exercise_id: str = Query(...),
    claims=Depends(auth.require_auth),
    workout_repo: DynamoWorkoutRepository = Depends(get_workout_repo),
    exercise_repo: DynamoExerciseRepository = Depends(get_exercise_repo),
    profile_repo: DynamoProfileRepository = Depends(get_profile_repo),
):
    user_sub = claims["sub"]

    exercise = exercise_repo.get_exercise_by_id(user_sub, exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    try:
        sets = workout_repo.get_sets_for_exercise(exercise_id)
    except WorkoutRepoError:
        logger.exception(
            f"Error fetching workout data for 1RM chart user_sub={user_sub}"
        )
        raise HTTPException(status_code=500, detail="Error fetching workout data")

    profile = profile_repo.get_for_user(user_sub)
    weight_unit = profile.weight_unit if profile else "kg"

    chart_data = progress.build_1rm_chart_data(sets, exercise_id, weight_unit)

    return render_template(
        request,
        "progress/_1rm_chart.html",
        context={
            "chart_data": chart_data,
            "exercise_name": exercise.name,
        },
    )
