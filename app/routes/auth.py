import requests
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.settings import settings
from app.utils.log import logger

router = APIRouter(prefix="/auth", tags=["auth"])

CLIENT_ID = settings.COGNITO_AUDIENCE
REDIRECT_URI = settings.COGNITO_REDIRECT_URI

COMMON_COOKIE_OPTS = {
    "httponly": True,
    "secure": True,
    "samesite": "lax",
}


def set_cookies(response: Response, token_data: dict) -> None:
    logger.debug("Setting auth cookies")
    response.set_cookie(
        key="id_token",
        value=token_data["id_token"],
        max_age=token_data["expires_in"],
        **COMMON_COOKIE_OPTS,
    )
    response.set_cookie(
        key="access_token",
        value=token_data["access_token"],
        max_age=token_data["expires_in"],
        **COMMON_COOKIE_OPTS,
    )
    response.set_cookie(
        key="refresh_token",
        value=token_data["refresh_token"],
        max_age=60 * 60 * 24 * 7,
        **COMMON_COOKIE_OPTS,
    )


@router.get("/login")
def auth_login(request: Request):

    login_url = (
        f"{settings.auth_url()}"
        f"?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid+email+profile"
    )
    logger.debug("Redirecting user to Cognito hosted UI")
    return RedirectResponse(url=login_url)


@router.get("/callback", name="auth_callback")
def auth_callback(request: Request, code: str):
    logger.debug("Received auth callback")

    if not code:
        logger.error("No authorization code provided in callback")
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Send token exchange request
    logger.debug("Exchanging authorization code with Cognito")
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response_token = requests.post(
        settings.token_url(), data=data, headers=headers, timeout=5
    )
    logger.debug(f"Token exchange status_code={response_token.status_code}")

    if response_token.status_code != 200:
        logger.error(f"Token exchange failed: {response_token.text}")
        raise HTTPException(status_code=400, detail="Token exchange failed")

    token_data = response_token.json()

    if token_data["token_type"] != "Bearer":
        logger.error("Invalid token type received from Cognito")
        raise HTTPException(status_code=400, detail="Invalid token type")

    logger.debug("Authentication successful; redirecting home and setting cookies")
    response = RedirectResponse("/", status_code=302)
    set_cookies(response, token_data)

    return response


@router.get("/logout")
async def logout(response: Response):
    logger.debug("User requested logout; clearing cookies")

    response = RedirectResponse(url="/", status_code=303)

    for cookie in ["id_token", "access_token", "refresh_token"]:
        logger.debug(f"Deleting cookie: {cookie}")
        response.delete_cookie(cookie)
    return response
