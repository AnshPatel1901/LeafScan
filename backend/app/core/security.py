"""
Security utilities: password hashing, JWT creation/verification.
All functions are pure and stateless — easy to unit-test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of *plain_password*."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────────────

TokenData = Dict[str, Any]

_ACCESS_TOKEN_TYPE = "access"
_REFRESH_TOKEN_TYPE = "refresh"


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: Optional[TokenData] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: TokenData = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_access_token(user_id: str) -> str:
    """Create a short-lived JWT access token for *user_id*."""
    return _create_token(
        subject=user_id,
        token_type=_ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token for *user_id*."""
    return _create_token(
        subject=user_id,
        token_type=_REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> TokenData:
    """
    Decode and verify *token*.

    Raises
    ------
    JWTError
        If the token is invalid, expired, or tampered with.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def decode_access_token(token: str) -> str:
    """
    Validate an access token and return the user_id (subject).

    Raises
    ------
    JWTError
        On any validation failure.
    """
    payload = decode_token(token)
    if payload.get("type") != _ACCESS_TOKEN_TYPE:
        raise JWTError("Invalid token type — expected access token")
    subject: Optional[str] = payload.get("sub")
    if subject is None:
        raise JWTError("Token has no subject")
    return subject


def decode_refresh_token(token: str) -> str:
    """
    Validate a refresh token and return the user_id (subject).

    Raises
    ------
    JWTError
        On any validation failure.
    """
    payload = decode_token(token)
    if payload.get("type") != _REFRESH_TOKEN_TYPE:
        raise JWTError("Invalid token type — expected refresh token")
    subject: Optional[str] = payload.get("sub")
    if subject is None:
        raise JWTError("Token has no subject")
    return subject
