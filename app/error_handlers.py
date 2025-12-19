from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.templates.templates import render_template
from app.utils.log import logger


async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login")
    return render_template(
        request,
        "error.html",
        context={
            "request": request,
            "status_code": exc.status_code,
            "message": exc.detail,
        },
        status_code=exc.status_code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")

    return render_template(
        request,
        "error.html",
        context={
            "request": request,
            "status_code": 500,
            "message": "Gremlins.",
        },
        status_code=500,
    )


def register_error_handlers(app: FastAPI) -> None:
    # ignore type check as function is expecting Exception type but we're giving it the more specific HTTPException
    # which is fine, but VS Code is panicking.
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
