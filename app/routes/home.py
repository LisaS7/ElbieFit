from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.templates.templates import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html")


@router.get("/healthz", response_class=JSONResponse)
def healthz():
    return {"status": "ok"}
