"""
User profile routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, UserProfile, PsychologicalProfile, Interest, user_interests
from app.schemas import (
    UserProfileCreate, UserProfileUpdate, UserProfileResponse,
    PsychologicalProfileCreate, PsychologicalProfileResponse,
    InterestCreate, InterestResponse
)
from app.auth import get_current_user
from app.ai_service import ai_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile"""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


@router.post("/me/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create user profile"""

    # Check if profile already exists
    existing_profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists"
        )

    # Create new profile
    new_profile = UserProfile(
        user_id=current_user.id,
        **profile_data.model_dump(exclude={'looking_for_gender'}),
        looking_for_gender=[g.value for g in profile_data.looking_for_gender],
        is_profile_complete=True
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return new_profile


@router.patch("/me/profile", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    # Update fields
    update_data = profile_data.model_dump(exclude_unset=True)
    if 'looking_for_gender' in update_data:
        update_data['looking_for_gender'] = [g.value for g in profile_data.looking_for_gender]

    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile


@router.get("/me/psychological-profile", response_model=PsychologicalProfileResponse)
async def get_psychological_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get psychological profile"""
    profile = db.query(PsychologicalProfile).filter(
        PsychologicalProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Psychological profile not found"
        )
    return profile


@router.post("/me/psychological-profile", response_model=PsychologicalProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_psychological_profile(
    profile_data: PsychologicalProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create psychological profile from questionnaire"""

    # Check if profile already exists
    existing_profile = db.query(PsychologicalProfile).filter(
        PsychologicalProfile.user_id == current_user.id
    ).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Psychological profile already exists"
        )

    # Create new profile
    new_profile = PsychologicalProfile(
        user_id=current_user.id,
        **profile_data.model_dump()
    )

    # Generate AI insights
    ai_insights = await ai_service.analyze_psychological_profile(
        profile_data.model_dump(),
        db
    )
    new_profile.ai_insights = ai_insights

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return new_profile


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    return profile.interests
