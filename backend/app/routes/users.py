"""
User profile routes (owner-only: every route operates on the current user)
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Interest, PsychologicalProfile, User, UserProfile, user_interests
from app.schemas import (
    InterestResponse,
    PsychologicalProfileResponse,
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
    validate_adult_dob,
)

router = APIRouter(prefix="/users", tags=["Users"])


def _get_own_profile(db: Session, user: User) -> Optional[UserProfile]:
    return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()


def _profile_values(data: dict) -> dict:
    """Convert validated schema data into ORM column values."""
    if data.get("looking_for_gender") is not None:
        data["looking_for_gender"] = [g.value for g in data["looking_for_gender"]]
    return data


def _body_error(field: str, msg: str) -> RequestValidationError:
    return RequestValidationError(
        [{"loc": ("body", field), "msg": msg, "type": "value_error"}]
    )


def _validate_merged(profile: UserProfile, update: dict) -> None:
    """Cross-field rules evaluated on the profile as it would be after PATCH."""
    def merged(field):
        return update[field] if field in update else getattr(profile, field)

    dob = merged("date_of_birth")
    if dob is not None and "date_of_birth" not in update:
        if isinstance(dob, date):
            try:
                validate_adult_dob(dob)
            except ValueError as exc:
                raise _body_error("date_of_birth", str(exc))

    lo, hi = merged("age_preference_min"), merged("age_preference_max")
    if lo is not None and hi is not None and lo > hi:
        field = "age_preference_min" if "age_preference_min" in update else "age_preference_max"
        raise _body_error(field, "age_preference_min must be <= age_preference_max")


@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's profile"""
    profile = _get_own_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.post(
    "/me/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED
)
def create_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create the current user's profile (400 if it already exists)."""
    if _get_own_profile(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists"
        )

    values = _profile_values(profile_data.model_dump())
    new_profile = UserProfile(user_id=current_user.id, is_profile_complete=True, **values)
    db.add(new_profile)
    try:
        db.commit()
    except IntegrityError:  # concurrent create for the same user
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists"
        )
    db.refresh(new_profile)
    return new_profile


@router.patch("/me/profile", response_model=UserProfileResponse)
def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partially update the current user's profile."""
    profile = _get_own_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    update_data = profile_data.model_dump(exclude_unset=True)
    _validate_merged(profile, update_data)

    for field, value in _profile_values(update_data).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me/psychological-profile", response_model=PsychologicalProfileResponse)
def get_psychological_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get psychological profile (computed server-side from the questionnaire)."""
    profile = db.query(PsychologicalProfile).filter(
        PsychologicalProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Psychological profile not found"
        )
    return profile


# NOTE: POST /users/me/psychological-profile was removed: it accepted
# client-computed scores. Profiles are created by POST /questionnaire/submit.


@router.get("/interests", response_model=List[InterestResponse])
def get_all_interests(db: Session = Depends(get_db)):
    """Get all available interests"""
    return db.query(Interest).all()


@router.post("/me/interests", status_code=status.HTTP_201_CREATED)
def add_user_interests(
    interest_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Replace the current user's interests"""
    profile = _get_own_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    db.execute(user_interests.delete().where(user_interests.c.user_id == current_user.id))

    valid_ids = {
        row[0]
        for row in db.query(Interest.id).filter(Interest.id.in_(set(interest_ids))).all()
    } if interest_ids else set()
    for interest_id in sorted(valid_ids):
        db.execute(
            user_interests.insert().values(user_id=current_user.id, interest_id=interest_id)
        )

    db.commit()
    return {"message": "Interests updated successfully"}


@router.get("/me/interests", response_model=List[InterestResponse])
def get_user_interests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's interests"""
    profile = _get_own_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile.interests
