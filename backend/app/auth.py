"""
Authentication utilities and dependencies.

JWT claims: sub (user id as string), type ("access" | "refresh"), iat, exp.
Access and refresh tokens are not interchangeable.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import AppError
from app.models import User
from app.schemas import TokenData

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Used to equalise login timing for unknown emails.
_DUMMY_HASH = pwd_context.hash("dummy-password-for-timing")

# HTTP Bearer token scheme; missing header is handled by us (401 NOT_AUTHENTICATED, not FastAPI's 403).
security = HTTPBearer(auto_error=False)

_BEARER = {"WWW-Authenticate": "Bearer"}

# Canonical positive user id as issued by _create_token (ASCII digits, no sign/padding/leading zero).
_SUB_RE = re.compile(r"[1-9][0-9]{0,17}")


def _unauthorized(code: str, message: str) -> AppError:
    return AppError(401, code, message, headers=_BEARER)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def _create_token(user_id: int, token_type: str, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    return _create_token(
        user_id, ACCESS_TOKEN_TYPE, expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token"""
    return _create_token(
        user_id, REFRESH_TOKEN_TYPE, expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def create_token_pair(user_id: int) -> dict:
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def decode_token(token: str, expected_type: str = ACCESS_TOKEN_TYPE) -> TokenData:
    """Decode and validate a JWT. Raises AppError(401 TOKEN_EXPIRED | INVALID_TOKEN)."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"require_exp": True}
        )
    except ExpiredSignatureError:
        raise _unauthorized("TOKEN_EXPIRED", "Token has expired")
    except JWTError:
        raise _unauthorized("INVALID_TOKEN", "Invalid token")

    if payload.get("type") != expected_type:
        raise _unauthorized("INVALID_TOKEN", "Invalid token")
    sub = payload.get("sub")
    if not isinstance(sub, str) or not _SUB_RE.fullmatch(sub):
        raise _unauthorized("INVALID_TOKEN", "Invalid token")
    return TokenData(user_id=int(sub))


def get_user_for_token(db: Session, token: str, expected_type: str = ACCESS_TOKEN_TYPE) -> User:
    """Resolve a token to an active user. Unknown user -> INVALID_TOKEN; inactive -> ACCOUNT_DISABLED."""
    token_data = decode_token(token, expected_type)
    user = db.get(User, token_data.user_id)
    if user is None:
        raise _unauthorized("INVALID_TOKEN", "Invalid token")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "Account is disabled")
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user"""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("NOT_AUTHENTICATED", "Not authenticated")
    return get_user_for_token(db, credentials.credentials, ACCESS_TOKEN_TYPE)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user (get_current_user already rejects inactive users)."""
    return current_user


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(func.lower(User.email) == normalize_email(email)).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password (case-insensitive email)."""
    user = get_user_by_email(db, email)
    if not user:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
