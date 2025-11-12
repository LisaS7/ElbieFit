from fastapi import FastAPI

from .routes import auth, home

app = FastAPI(title="ElbieFit")

app.include_router(home.router)
app.include_router(auth.router)
