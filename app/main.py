from fastapi import FastAPI

from .error_handlers import register_error_handlers
from .routes import auth, home, profile, workout

app = FastAPI(title="ElbieFit")

register_error_handlers(app)

app.include_router(home.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(workout.router)
