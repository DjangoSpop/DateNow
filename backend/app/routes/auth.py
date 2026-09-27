"""
Authentication routes
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_token_pair,
    enforce_rate_limit,
    get_current_user,
    get_password_hash,
    get_user_from_refresh_token,
    rate_limit_by_ip,
)
from app.database import get_db
from app.models import OnboardingProgress, OnboardingStatus, User, UserProfile
from app.schemas import MeResponse, RefreshRequest, Token, UserLogin, UserRegister

router = APIRouter(prefix="/auth", tags=["Authentication"])

_DUPLICATE_EMAIL = "Email already registered"


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_by_ip)],
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user. Emails are stored lower-cased; duplicates -> 409."""
    email = user_data.email  # already normalised by the schema

    if db.query(User.id).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_EMAIL)

    new_user = User(
        email=email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:  # concurrent registration with the same email
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_EMAIL)
    db.refresh(new_user)

    return Token(**create_token_pair(new_user.id))


@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit_by_ip)])
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    enforce_rate_limit(f"login:email:{credentials.email}")

    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    return Token(**create_token_pair(user.id))


@router.post("/refresh", response_model=Token)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    user = get_user_from_refresh_token(db, body.refresh_token)
    return Token(**create_token_pair(user.id))


@router.get("/me", response_model=MeResponse)
def read_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Current user plus the state the mobile app needs on boot."""
    has_profile = (
        db.query(UserProfile.id).filter(UserProfile.user_id == current_user.id).first()
        is not None
    )
    progress_status = (
        db.query(OnboardingProgress.status)
        .filter(OnboardingProgress.user_id == current_user.id)
        .scalar()
    )
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        has_profile=has_profile,
        onboarding_status=progress_status or OnboardingStatus.NOT_STARTED,
    )
