from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from app.utils.auth import require_auth

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(user=Depends(require_auth)):
    return """
<html>
      <head><title>ElbieFit</title></head>
      <body>
        <h1>Welcome to ElbieFit</h1>
        <p>Login successful! You’ve reached the home page. Well done.</p>
      </body>
    </html>
"""


@router.get("/healthz", response_class=JSONResponse)
def healthz():
    return {"status": "ok"}
