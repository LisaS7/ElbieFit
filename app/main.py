from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.templates.templates import templates
from app.utils.log import logger

from .routes import auth, home, profile

app = FastAPI(title="ElbieFit")


# TODO: this should probably go somewhere else. eventually.
@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "message": exc.detail,
        },
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "message": "Gremlins.",
        },
        status_code=500,
    )


app.include_router(home.router)
app.include_router(auth.router)
app.include_router(profile.router)
