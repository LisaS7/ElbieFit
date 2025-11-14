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
    "samesite": "none",
}


def cognito_base_url() -> str:
    return f"https://{settings.COGNITO_DOMAIN}.auth.{settings.REGION}.amazoncognito.com"


def auth_url() -> str:
    return f"{cognito_base_url()}/oauth2/authorize"


def token_url() -> str:
    return f"{cognito_base_url()}/oauth2/token"


def set_cookies(response: Response, token_data: dict) -> None:
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
        f"{auth_url()}"
        f"?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid+email+profile"
    )
    return RedirectResponse(url=login_url)


@router.get("/callback", name="auth_callback")
def auth_callback(request: Request, code: str):
    if not code:
        logger.error("No authorization code provided in callback")
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Send token exchange request
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response_token = requests.post(token_url(), data=data, headers=headers)

    if response_token.status_code != 200:
        logger.error(f"Token exchange failed: {response_token.text}")
        raise HTTPException(status_code=400, detail="Token exchange failed")

    token_data = response_token.json()

    if token_data["token_type"] != "Bearer":
        logger.error("Invalid token type received")
        raise HTTPException(status_code=400, detail="Invalid token type")

    # Redirect to home page after successful authentication
    response = RedirectResponse("/", status_code=302)

    # Yummy cookies
    set_cookies(response, token_data)

    return response


@router.get("/logout")
async def protected_route(response: Response):
    response = RedirectResponse(url="/", status_code=303)

    for cookie in ["id_token", "access_token", "refresh_token"]:
        response.delete_cookie(cookie)
    return response
