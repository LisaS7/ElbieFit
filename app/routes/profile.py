from fastapi import APIRouter, Depends, HTTPException, Request

from app.templates.templates import templates
from app.utils import auth, dates, db
from app.utils.log import logger

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/")
def profile(request: Request, claims=Depends(auth.require_auth)):
    """Get the profile of the current authenticated user."""
    user_sub = claims["sub"]

    logger.info(f"Fetching profile for user_sub={user_sub}")

    try:
        profile = db.get_user_profile(user_sub)
    except Exception as e:
        logger.exception(f"Error fetching user profile: {e}")
        raise HTTPException(status_code=500, detail="Internal error reading profile")

    if not profile:
        logger.warning(f"No profile found for user_sub={user_sub}")
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                "request": request,
                "profile": None,
                "user_sub": user_sub,
            },
            status_code=404,
        )

    raw = profile.get("created_at")
    if raw:
        dt = dates.iso_to_dt(raw)
        profile["created_at_readable"] = dt.strftime("%d %B %Y")

    logger.debug(f"Profile retrieved: {profile}")
    return templates.TemplateResponse(
        request,
        "profile.html",
        {"request": request, "profile": profile, "user_sub": user_sub},
        status_code=200,
    )
