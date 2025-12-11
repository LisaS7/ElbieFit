import platform
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from settings import settings

from app.templates.templates import templates

router = APIRouter()

BUILD_TIME = datetime.utcnow().isoformat()


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
    }
