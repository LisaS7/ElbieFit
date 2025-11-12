from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from .routes import auth, home

app = FastAPI(title="ElbieFit")


# TODO: this should probably go somewhere else. eventually.
@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login")
    raise exc


app.include_router(home.router)
app.include_router(auth.router)
