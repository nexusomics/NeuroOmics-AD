"""Security helpers: password hashing (bcrypt), JWT creation/validation."""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (salt auto-generated, 12 rounds)."""
    pwd = password.encode("utf-8")[:72]  # bcrypt hard limit is 72 bytes
    return bcrypt.hashpw(pwd, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash (constant-time)."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access", "iat": dt.datetime.now(dt.timezone.utc)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh", "iat": dt.datetime.now(dt.timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> Optional[dict[str, Any]]:
    """Decode & validate a JWT. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.PyJWTError:
        return None
