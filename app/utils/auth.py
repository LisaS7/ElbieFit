import os
from datetime import datetime, timezone

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from jwt import PyJWKClient


def get_jwks_url(region, issuer):

    if not region or not issuer:
        raise HTTPException(
            status_code=500,
            detail="Missing REGION or COGNITO_ISSUER in environment variables.",
        )

    # Construct JWKS URL
    jwks_url = (
        f"https://cognito-idp.{region}.amazonaws.com/{issuer}/.well-known/jwks.json"
    )

    return jwks_url


async def require_auth(request: Request):
    # Extract the access token
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=401, detail="Access token is missing. Login again."
        )

    load_dotenv()
    REGION = os.getenv("REGION")
    ISSUER = os.getenv("COGNITO_ISSUER")
    AUDIENCE = os.getenv("COGNITO_AUDIENCE")

    jwks_url = get_jwks_url(REGION, ISSUER)
    expected_issuer = f"https://cognito-idp.{REGION}.amazonaws.com/{ISSUER}"

    try:
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(access_token).key

        decoded_token = jwt.decode(
            access_token,
            signing_key,
            algorithms=["RS256"],
            issuer=expected_issuer,
            audience=AUDIENCE,
        )
        exp = decoded_token.get("exp")
        exp_time = (
            datetime.fromtimestamp(exp, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
            if exp
            else None
        )

        decoded_token["_exp_str"] = exp_time

        return decoded_token

    except jwt.ExpiredSignatureError:
        return {"error": "JWT token has expired"}
    except jwt.InvalidSignatureError:
        return {"error": "Invalid signature"}
    except jwt.InvalidTokenError as e:
        return {"error": f"Invalid token: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
