"""
User routes: current user, profile, psychological profile (read-only), interests.

Profile and psychological-profile routes never call the AI service.
"""
from datetime import datetime, time
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.errors import AppError
from app.models import Interest, PsychologicalProfile, User, UserProfile, user_interests
from app.schemas import (
    InterestResponse,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
    PsychologicalProfileResponse,
    UserMeResponse,
    age_on,
    utc_today,
)
from app.services.onboarding import onboarding_status

router = APIRouter(prefix="/users", tags=["Users"])


def _profile_not_found() -> AppError:
    return AppError(404, "PROFILE_NOT_FOUND", "Profile not found")


def _get_own_profile(db: Session, user: User) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        raise _profile_not_found()
    return profile


def _profile_response(profile: UserProfile) -> ProfileResponse:
    dob = profile.date_of_birth.date() if isinstance(profile.date_of_birth, datetime) else profile.date_of_birth
    return ProfileResponse(
        first_name=profile.first_name,
        last_name=profile.last_name,
        date_of_birth=dob,
        age=age_on(dob, utc_today()),
        gender=profile.gender,
        looking_for_gender=profile.looking_for_gender or [],
        age_preference_min=profile.age_preference_min,
        age_preference_max=profile.age_preference_max,
        relationship_goal=profile.relationship_goal,
        bio=profile.bio,
        city=profile.city,
        country=profile.country,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _to_columns(data: dict) -> dict:
    """Convert validated schema values to column values."""
    out = dict(data)
    if out.get("looking_for_gender") is not None:
        out["looking_for_gender"] = [g.value for g in out["looking_for_gender"]]
    if out.get("date_of_birth") is not None:
        # The baseline column is a (naive) DateTime; store midnight of the given date.
        out["date_of_birth"] = datetime.combine(out["date_of_birth"], time.min)
    return out


def _check_age_range(age_min: int, age_max: int) -> None:
    if age_min is not None and age_max is not None and age_min > age_max:
        raise AppError(
            422, "VALIDATION_ERROR", "Request validation failed",
            fields={"age_preference_max": "must be greater than or equal to age_preference_min"},
        )


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Current user plus onboarding state (the mobile app routes on `onboarding`)."""
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        is_verified=bool(current_user.is_verified),
        created_at=current_user.created_at,
        onboarding=onboarding_status(db, current_user),
    )


@router.get("/me/profile", response_model=ProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's profile"""
    return _profile_response(_get_own_profile(db, current_user))


@router.post("/me/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create the current user's profile"""
    _check_age_range(profile_data.age_preference_min, profile_data.age_preference_max)

    if db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first():
        raise AppError(409, "PROFILE_EXISTS", "Profile already exists")

    profile = UserProfile(
        user_id=current_user.id,
        **_to_columns(profile_data.model_dump()),
        is_profile_complete=True,
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:  # concurrent create (user_id is unique)
        db.rollback()
        raise AppError(409, "PROFILE_EXISTS", "Profile already exists")
    db.refresh(profile)
    return _profile_response(profile)


@router.patch("/me/profile", response_model=ProfileResponse)
def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partially update the current user's profile (only fields present are changed)."""
    profile = _get_own_profile(db, current_user)
    update_data = _to_columns(profile_data.model_dump(exclude_unset=True))

    _check_age_range(
        update_data.get("age_preference_min", profile.age_preference_min),
        update_data.get("age_preference_max", profile.age_preference_max),
    )

    for field, value in update_data.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return _profile_response(profile)


@router.get("/me/psychological-profile", response_model=PsychologicalProfileResponse)
def get_psychological_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the current user's (server-computed) psychological profile"""
    profile = db.query(PsychologicalProfile).filter(PsychologicalProfile.user_id == current_user.id).first()
    if not profile:
        raise AppError(404, "PSYCH_PROFILE_NOT_FOUND", "Psychological profile not found")
    return PsychologicalProfileResponse.from_model(profile)


@router.get("/interests", response_model=List[InterestResponse])
async def get_all_interests(db: Session = Depends(get_db)):
    """Get all available interests"""
    interests = db.query(Interest).all()
    return interests


@router.post("/me/interests", status_code=status.HTTP_201_CREATED)
async def add_user_interests(
    interest_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add interests to user profile"""

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise _profile_not_found()

    # Clear existing interests
    db.execute(user_interests.delete().where(user_interests.c.user_id == current_user.id))

    # Add new interests
    for interest_id in interest_ids:
        interest = db.query(Interest).filter(Interest.id == interest_id).first()
        if interest:
            db.execute(
                user_interests.insert().values(user_id=current_user.id, interest_id=interest_id)
            )

    db.commit()

    return {"message": "Interests updated successfully"}


@router.get("/me/interests", response_model=List[InterestResponse])
async def get_user_interests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's interests"""

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise _profile_not_found()

    return profile.interests
