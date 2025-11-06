# app/utils.py
import hmac, hashlib, os
from datetime import datetime, timedelta
from jose import jwt

SECRET = os.environ.get("KYC_SIGN_KEY", "dev-secret-key")
JWT_ALG = "HS256"

def sign_token(payload: dict) -> str:
    """Return a compact JWT signature for payload. In prod, use HSM/RSA."""
    token = jwt.encode(payload, SECRET, algorithm=JWT_ALG)
    return token

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=[JWT_ALG])
    except Exception:
        return {}
    
def hash_value(val: str) -> str:
    return hashlib.sha256(val.encode()).hexdigest()
