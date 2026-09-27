"""
Authentication utilities and dependencies
"""
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Deque, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData


TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# Only HS256 is ever accepted, regardless of configuration (config also
# validates JWT_ALGORITHM == "HS256").
JWT_ALGORITHM = "HS256"
_ALLOWED_ALGORITHMS = [JWT_ALGORITHM]

_DECODE_OPTIONS = {
    "verify_signature": True,
    "verify_exp": True,
    "verify_iat": True,
    "verify_sub": True,
    "require_exp": True,
    "require_iat": True,
    "require_sub": True,
}

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme. auto_error=False so that a missing/garbled
# Authorization header yields 401 (FastAPI's default is 403).
security = HTTPBearer(auto_error=False)


def _credentials_exception(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return pwd_context.hash("timing-equaliser-not-a-real-password")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password.

    Runs a bcrypt verification even for unknown emails so response timing does
    not reveal whether an account exists.
    """
    user = db.query(User).filter(User.email == normalize_email(email)).first()
    if not user:
        verify_password(password, _dummy_password_hash())
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def _create_token(data: dict, token_type: str, expires_delta: timedelta) -> str:
    if "sub" not in data or data["sub"] is None:
        raise ValueError("token data must include 'sub'")
    now = datetime.now(timezone.utc)
    to_encode = dict(data)
    to_encode.update({
        "sub": str(data["sub"]),  # RFC 7519 / python-jose require a string subject
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token. ``data`` must contain ``sub`` (the user id)."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(data, TOKEN_TYPE_ACCESS, expires_delta)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token. ``data`` must contain ``sub`` (the user id)."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(data, TOKEN_TYPE_REFRESH, expires_delta)


def create_token_pair(user_id: int) -> dict:
    return {
        "access_token": create_access_token({"sub": user_id}),
        "refresh_token": create_refresh_token({"sub": user_id}),
        "token_type": "bearer",
    }


def _parse_subject(sub) -> int:
    if not isinstance(sub, str) or not sub.isascii() or not sub.isdigit() or len(sub) > 18:
        raise ValueError("invalid subject")
    user_id = int(sub)
    if user_id <= 0:
        raise ValueError("invalid subject")
    return user_id


def decode_token(token: str, expected_type: str = TOKEN_TYPE_ACCESS) -> TokenData:
    """Decode and validate a JWT; raises 401 on any problem.

    Checks signature (HS256 only), ``exp``/``iat``/``sub`` presence, that
    ``sub`` is a positive integer string and that ``type`` matches
    ``expected_type``.
    """
    credentials_exception = _credentials_exception()
    if not token or not isinstance(token, str):
        raise credentials_exception
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=_ALLOWED_ALGORITHMS,
            options=_DECODE_OPTIONS,
        )
    except JWTError:
        raise credentials_exception
    except Exception:  # malformed input that slips past jose's own handling
        raise credentials_exception

    if payload.get("type") != expected_type:
        raise credentials_exception
    try:
        user_id = _parse_subject(payload.get("sub"))
    except ValueError:
        raise credentials_exception
    return TokenData(user_id=user_id)


def _load_active_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise _credentials_exception()
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def get_user_from_refresh_token(db: Session, refresh_token: str) -> User:
    token_data = decode_token(refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    return _load_active_user(db, token_data.user_id)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user (401 if unauthenticated, 403 if inactive)."""
    if credentials is None or not credentials.credentials:
        raise _credentials_exception("Not authenticated")
    token_data = decode_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
    return _load_active_user(db, token_data.user_id)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


# ---------------------------------------------------------------------------
# Rate limiting for auth endpoints
# ---------------------------------------------------------------------------

class SlidingWindowRateLimiter:
    """Minimal in-process sliding-window limiter.

    NOTE: state lives in this process only. With several workers/instances each
    one keeps its own counters; a Redis-backed limiter should replace this
    before horizontal scaling.
    """

    def __init__(self, window_seconds: float = 60.0):
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int) -> Optional[int]:
        """Record an attempt. Returns None if allowed, else seconds until retry."""
        if limit <= 0:
            return None
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= limit:
                return max(1, int(q[0] + self.window_seconds - now) + 1)
            q.append(now)
            if len(self._hits) > 10_000:
                self._prune(cutoff)
            return None

    def _prune(self, cutoff: float) -> None:
        for k in [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]:
            del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_rate_limiter = SlidingWindowRateLimiter(window_seconds=60.0)


def enforce_rate_limit(key: str) -> None:
    retry_after = auth_rate_limiter.hit(key, settings.AUTH_RATE_LIMIT_PER_MINUTE)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please try again later",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit_by_ip(request: Request) -> None:
    """Dependency: per-client-IP limit keyed by route path.

    Uses the direct peer address; X-Forwarded-For is not trusted here.
    """
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"{request.url.path}:ip:{client_ip}")
