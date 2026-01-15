from fastapi import Response

from app.repositories.profile import DynamoProfileRepository
from app.settings import settings
from app.utils.auth import decode_and_validate_id_token, get_jwks_url

THEME_COOKIE_OPTS = {
    "httponly": True,
    "secure": True,
    "samesite": "lax",
    "path": "/",
}


def set_theme_cookie(response: Response, theme: str) -> None:
    response.set_cookie(
        key="theme",
        value=theme,
        max_age=60 * 60 * 24 * 365,  # 1 year
        **THEME_COOKIE_OPTS,
    )


def get_theme_cookie_from_profile(response: Response, id_token: str) -> None:
    """
    After a successful login, set the theme cookie based on the user's stored profile.
    If profile/theme doesn't exist, do nothing (middleware will use DEFAULT_THEME).
    """

    claims = decode_and_validate_id_token(
        id_token=id_token,
        jwks_url=get_jwks_url((settings.COGNITO_ISSUER_URL or "").rstrip("/")),
        issuer=(settings.COGNITO_ISSUER_URL or "").rstrip("/"),
        audience=settings.COGNITO_AUDIENCE,
    )
    user_sub = claims.get("sub")

    if not user_sub:
        return

    repo = DynamoProfileRepository()

    try:
        profile = repo.get_for_user(user_sub)
    except Exception:
        # don't fail login over theme; just fall back to default
        return

    theme = getattr(getattr(profile, "preferences", None), "theme", None)
    if not theme:
        return

    if hasattr(settings, "THEMES") and theme not in settings.THEMES:
        return

    set_theme_cookie(response, theme)
