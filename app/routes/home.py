import json
import platform
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.repositories.workout import WorkoutRepository
from app.routes.workout import get_workout_repo
from app.settings import settings
from app.templates.templates import render_template
from app.utils import auth
from app.utils.dates import now
from app.utils.log import logger

router = APIRouter()


def load_git_meta():  # pragma: no cover
    meta_file = Path(__file__).parent.parent / "git_meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text())
    return {}


GIT_META = load_git_meta()
BUILD_TIME = now()


@router.get("/")
def home(
    request: Request,
    repo: WorkoutRepository = Depends(get_workout_repo),
):
    # If not auth, show generic page
    try:
        claims = auth.require_auth(request)
    except HTTPException:
        return render_template(request, "home.html", context={"is_authed": False})

    user_sub = claims["sub"]
    try:
        workouts = repo.get_all_for_user(user_sub)
    except Exception:
        logger.exception(f"Error fetching workouts for user_sub={user_sub}")
        workouts = []

    # “Recent” can be done by sorting in Python until we add a repo method
    recent = sorted(workouts, key=lambda w: w.date, reverse=True)[:5]

    return render_template(
        request,
        "home.html",
        context={
            "is_authed": True,
            "recent_workouts": recent,
        },
    )


@router.get("/healthz", response_class=JSONResponse)
def healthz():
    return {"status": "ok"}


@router.get("/meta")
async def get_meta():
    return {
        "app_name": "ElbieFit",
        "version": "0.1.0",
        "build_time": BUILD_TIME,
        "python_version": platform.python_version(),
        "environment": settings.ENV,
        **GIT_META,
    }
