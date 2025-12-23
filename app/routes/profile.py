from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, HTTPException, Request

from app.repositories.profile import DynamoProfileRepository, ProfileRepository
from app.settings import settings
from app.templates.templates import render_template
from app.utils import auth
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
        return render_template(
            request,
            "profile/profile.html",
            context={
                "request": request,
                "profile": None,
                "user_sub": user_sub,
            },
            status_code=404,
        )

    tz_options = sorted(available_timezones())
    is_demo_user = bool(settings.DEMO_USER_SUB and user_sub == settings.DEMO_USER_SUB)

    logger.debug(f"Profile retrieved for user_sub={user_sub}")

    return render_template(
        request,
        "profile/profile.html",
        context={
            "request": request,
            "profile": profile,
            "user_sub": user_sub,
            "tz_options": tz_options,
            "is_demo_user": is_demo_user,
            # placeholders for card swaps / validation later
            "account_form": None,
            "account_errors": None,
            "account_success": False,
            "prefs_form": None,
            "prefs_errors": None,
            "prefs_success": False,
        },
        status_code=200,
    )
