"""
HC-XCDSS Password Hashing & JWT Token Utilities
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt

# --------------------------------------------------
# Password Hashing Utilities (Native bcrypt)
# --------------------------------------------------

def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt (salted).
    """
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


# --------------------------------------------------
# JWT Configuration & Production Hardening
# --------------------------------------------------

INSECURE_DEV_FALLBACK_KEY = "hc_xcdss_dev_insecure_secret_key_change_in_production_38472918"


def get_jwt_secret_key() -> str:
    """
    Resolve JWT secret key with environment-aware security validation:
    - In production (ENVIRONMENT/APP_ENV/ENV in ['production', 'prod']), an explicit,
      non-default JWT_SECRET_KEY is strictly required.
    - If missing or equal to the dev fallback in production, raises a RuntimeError.
    - In development/testing, falls back to the development secret key.
    """
    env = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", os.getenv("ENV", "development"))).strip().lower()
    is_production = env in {"production", "prod"}

    secret = os.getenv("JWT_SECRET_KEY")
    if is_production:
        if not secret or not secret.strip() or secret.strip() == INSECURE_DEV_FALLBACK_KEY:
            raise RuntimeError(
                "Production security error: JWT_SECRET_KEY environment variable "
                "must be explicitly set to a secure secret in production mode. "
                "Default or empty keys are strictly prohibited."
            )
        return secret.strip()

    return secret.strip() if secret and secret.strip() else INSECURE_DEV_FALLBACK_KEY


def validate_jwt_configuration() -> None:
    """
    Explicit startup validation helper.
    """
    get_jwt_secret_key()


JWT_SECRET_KEY = get_jwt_secret_key()
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token.
    """
    secret_key = get_jwt_secret_key()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token. Raises jwt.PyJWTError on failure.
    """
    secret_key = get_jwt_secret_key()
    return jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])

