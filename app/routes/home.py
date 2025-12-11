import json
import platform
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.settings import settings
from app.templates.templates import templates
from app.utils.dates import now

router = APIRouter()


def load_git_meta():
    meta_file = Path(__file__).parent.parent / "git_meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text())
    return {}


GIT_META = load_git_meta()
BUILD_TIME = now()


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html")


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
