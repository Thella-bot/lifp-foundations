import hashlib
import os
import time
from jose import jwt

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_change_in_prod")
ALGORITHM = "HS256"
MOSIP_ISSUER = "https://mosip.local"

def hash_uin(uin: str) -> str:
    return hashlib.sha256(uin.encode()).hexdigest()

def create_mock_token(uin: str) -> str:
    internal_id = hash_uin(uin)
    claims = {
        "iss": MOSIP_ISSUER,
        "sub": internal_id,
        "uin": uin,
        "name": "John Doe",
        "gender": "M",
        "birthdate": "1990-01-01",
        "aud": "lifp",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience="lifp")