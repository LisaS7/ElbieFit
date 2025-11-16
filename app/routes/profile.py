from fastapi import APIRouter, Depends, HTTPException, Request

from app.repositories.profile import DynamoProfileRepository, ProfileRepository
from app.templates.templates import templates
from app.utils import auth, dates
from app.utils.log import logger

router = APIRouter(prefix="/profile", tags=["profile"])


def get_profile_repo() -> ProfileRepository:  # pragma: no cover
    return DynamoProfileRepository()


@router.get("/")
def profile(
    request: Request,
    claims=Depends(auth.require_auth),
    repo: ProfileRepository = Depends(get_profile_repo),
):
    """Get the profile of the current authenticated user."""
    user_sub = claims["sub"]

    logger.info(f"Fetching profile for user_sub={user_sub}")

    try:
        profile = repo.get_for_user(user_sub)
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
