"""
shared/security.py
JWT verification and reusable FastAPI auth helpers.
"""

import os
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set.")

ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
AUDIENCE = os.environ.get("JWT_AUDIENCE", "lifp")
ISSUER = os.environ.get("JWT_ISSUER")  # optional


def verify_access_token(token: str, expected_sub: Optional[str] = None) -> dict:
    """Verify a LIFP JWT. Raises jose.JWTError on any failure."""
    options = {"verify_aud": True}
    claims = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=ISSUER if ISSUER else None,
        options=options,
    )

    if expected_sub and claims.get("sub") != expected_sub:
        raise JWTError("Token subject does not match expected principal.")
    return claims


def get_internal_id(token: str) -> str:
    """Convenience: verify and return the subject (internal_id)."""
    return verify_access_token(token)["sub"]


def extract_bearer_token(authorization: Optional[str]) -> str:
    """Extract bearer token from Authorization header or raise 401."""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")
    return token


def require_internal_id_from_header(
    authorization: Optional[str],
    expected_sub: Optional[str] = None,
) -> str:
    """Reusable FastAPI helper: parse bearer token and return verified subject."""
    token = extract_bearer_token(authorization)
    try:
        claims = verify_access_token(token, expected_sub=expected_sub)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return claims["sub"]
