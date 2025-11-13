from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, Request
from jwt import InvalidTokenError, PyJWKClient

from app.settings import settings
from app.utils.log import logger

REGION = settings.REGION
ISSUER = settings.COGNITO_ISSUER
AUDIENCE = settings.COGNITO_AUDIENCE


def get_jwks_url(region, issuer):
    """
    Build and return the JWKS (JSON Web Key Set) endpoint URL for a Cognito user pool.

    Cognito publishes its public signing keys at a well-known JWKS URL using the pattern:
        https://cognito-idp.<region>.amazonaws.com/<user_pool_id>/.well-known/jwks.json

    These keys are used to verify the signatures of ID and access tokens issued by that pool.
    """

    if not region or not issuer:
        logger.error("Missing REGION or COGNITO_ISSUER env vars")
        raise HTTPException(
            status_code=500,
            detail="Missing REGION or COGNITO_ISSUER in environment variables.",
        )

    # Construct JWKS URL
    jwks_url = f"{issuer}/.well-known/jwks.json"

    return jwks_url


async def require_auth(request: Request):
    """
    Validate ID token from cookies and return decoded claims.
    """

    # Extract the access token
    id_token = request.cookies.get("id_token")
    if not id_token:
        logger.warning("ID token missing from cookies")
        raise HTTPException(status_code=401, detail="ID token is missing. Login again.")

    logger.debug("ID token found in cookies")

    jwks_url = get_jwks_url(REGION, ISSUER)

    try:
        # Decode headers and get the kid
        unverified_headers = jwt.get_unverified_header(id_token)
        kid = unverified_headers.get("kid")
        logger.debug(f"Token header KID: {kid}")

        # Fetch signing key
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token).key

        decoded_token = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        if decoded_token.get("token_use") != "id":
            logger.error(
                f"Token 'token_use' mismatch: expected 'id', got {decoded_token.get('token_use')}"
            )
            raise HTTPException(status_code=401, detail="Wrong token type")

        exp = decoded_token.get("exp")
        exp_time = (
            datetime.fromtimestamp(exp, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
            if exp
            else None
        )

        decoded_token["_exp_str"] = exp_time

        sub = decoded_token.get("sub")
        logger.info(f"Authenticated user sub={sub}, token exp={exp_time}")

        return decoded_token

    except jwt.ExpiredSignatureError:
        logger.warning("ID token expired")
        raise HTTPException(status_code=401, detail="Token expired")

    except InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

    except Exception as e:
        # safety net for debugging — but NOT leaking token
        logger.exception(f"Unexpected error during token validation: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
