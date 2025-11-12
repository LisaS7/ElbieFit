import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.settings import settings
from app.utils import auth, db
from app.utils.log import logger

router = APIRouter(prefix="/auth", tags=["auth"])

CLIENT_ID = settings.COGNITO_AUDIENCE
REGION = settings.REGION
DOMAIN = settings.COGNITO_DOMAIN
REDIRECT_URI = settings.COGNITO_REDIRECT_URI


@router.get("/login")
def auth_login(request: Request):

    login_url = (
        f"https://{DOMAIN}.auth.{REGION}.amazoncognito.com/oauth2/authorize"
        f"?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid+email+profile"
    )
    return RedirectResponse(url=login_url)


@router.get("/callback", name="auth_callback")
def auth_callback(request: Request, code: str, response: Response):
    if not code:
        logger.error("No authorization code provided in callback")
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Send token exchange request
    token_endpoint = f"https://{DOMAIN}.auth.{REGION}.amazoncognito.com/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response_token = requests.post(token_endpoint, data=data, headers=headers)

    if response_token.status_code != 200:
        logger.error(f"Token exchange failed: {response_token.text}")
        raise HTTPException(status_code=400, detail="Token exchange failed")

    response_data = response_token.json()

    if response_data["token_type"] != "Bearer":
        logger.error("Invalid token type received")
        raise HTTPException(status_code=400, detail="Invalid token type")

    # Redirect to home page after successful authentication
    response = RedirectResponse("/auth/me", status_code=302)  # TODO: check code

    # TODO: tidy repeated arguments
    # Yummy cookies
    response.set_cookie(
        key="id_token",
        value=response_data["id_token"],
        max_age=response_data["expires_in"],
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        key="access_token",
        value=response_data["access_token"],
        max_age=response_data["expires_in"],
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        key="refresh_token",
        value=response_data["refresh_token"],
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        secure=True,
        samesite="none",
    )

    return response


@router.get("/me")
def me(claims=Depends(auth.require_auth)):
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
        raise HTTPException(status_code=404, detail="User profile not found")

    logger.debug(f"Profile retrieved: {profile}")
    return {"id": user_sub, "profile": profile}


@router.get("/logout")
async def protected_route(response: Response):
    response = RedirectResponse(url="/", status_code=303)
    # delete cookies here
    response.delete_cookie("id_token")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
