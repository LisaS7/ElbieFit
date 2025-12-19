from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.middleware.rate_limit import RateLimitMiddleware

from .error_handlers import register_error_handlers
from .routes import auth, demo, exercise, home, profile, workout

app = FastAPI(title="ElbieFit")

app.mount("/static", StaticFiles(directory="static"), name="static")

register_error_handlers(app)
app.add_middleware(RateLimitMiddleware)

app.include_router(home.router)
app.include_router(auth.router)
app.include_router(demo.router)
app.include_router(profile.router)
app.include_router(workout.router)
app.include_router(exercise.router)
