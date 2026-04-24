"""
shared/security.py
JWT verification used by ACSE and any future service that consumes tokens
issued by the identity service.
"""
import os

from jose import jwt, JWTError   # noqa: F401  (JWTError re-exported for callers)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set.")

ALGORITHM = "HS256"
AUDIENCE  = "lifp"

# Production upgrade path:
# 1. Generate RSA keypair:  openssl genrsa -out private.pem 2048
#                           openssl rsa -in private.pem -pubout -out public.pem
# 2. Identity service signs with private.pem (ALGORITHM = "RS256")
# 3. All other services verify with public.pem stored in SECRET_KEY
# 4. Change ALGORITHM = "RS256" here and pass the PEM string as SECRET_KEY


def verify_access_token(token: str) -> dict:
    """Verify a LIFP JWT. Raises jose.JWTError on any failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=AUDIENCE)


def get_internal_id(token: str) -> str:
    """Convenience: verify and return the subject (internal_id)."""
    return verify_access_token(token)["sub"]
