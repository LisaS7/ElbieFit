from fastapi import APIRouter, Depends, HTTPException, Response

from app.settings import settings
from app.utils.auth import require_auth
from app.utils.demo import enforce_cooldown, reset_user
from app.utils.log import logger

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", status_code=204)
def reset_demo(
    claims=Depends(require_auth),
):
    user_sub = claims["sub"]

    if not settings.DEMO_USER_SUB:
        logger.warning("Demo reset attempted but no demo sub exists")
        raise HTTPException(status_code=404)

    if user_sub != settings.DEMO_USER_SUB:
        logger.warning(f"Non-demo user attempted demo reset. Sub: {user_sub}")
        raise HTTPException(status_code=403)

    enforce_cooldown(user_sub, settings.DEMO_RESET_COOLDOWN_SECONDS)

    logger.info(f"Resetting demo user data. Sub: {user_sub}")

    reset_user(user_sub)

    return Response(status_code=204, headers={"HX-Trigger": "demoResetDone"})
