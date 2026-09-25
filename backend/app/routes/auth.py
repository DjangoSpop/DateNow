"""
Authentication routes
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    REFRESH_TOKEN_TYPE,
    authenticate_user,
    create_token_pair,
    get_password_hash,
    get_user_by_email,
    get_user_for_token,
)
from app.database import get_db
from app.errors import AppError
from app.models import User
from app.schemas import RefreshRequest, Token, UserLogin, UserRegister

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _email_taken() -> AppError:
    return AppError(409, "EMAIL_TAKEN", "Email already registered", fields={"email": "already registered"})


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user (email is trimmed and lower-cased)."""
    if get_user_by_email(db, user_data.email):
        raise _email_taken()

    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:  # concurrent registration with the same email
        db.rollback()
        raise _email_taken()
    db.refresh(new_user)

    return create_token_pair(new_user.id)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise AppError(401, "INVALID_CREDENTIALS", "Incorrect email or password")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "Account is disabled")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    return create_token_pair(user.id)


@router.post("/refresh", response_model=Token)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access + refresh token pair."""
    user = get_user_for_token(db, body.refresh_token, REFRESH_TOKEN_TYPE)
    return create_token_pair(user.id)
