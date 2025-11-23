"""
Matching and AI-mediated conversation routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import (
    User, UserProfile, PsychologicalProfile, Match, MatchStatus,
    AISession, AISessionStatus
)
from app.schemas import (
    MatchResponse, MatchActionRequest,
    AISessionResponse, AIQuestionResponse, AIResponseSubmit
)
from app.auth import get_current_user
from app.ai_service import ai_service
from app.config import settings

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get("/suggestions", response_model=List[MatchResponse])
async def get_match_suggestions(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized match suggestions"""

    # Get current user's profiles
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    user_psych = db.query(PsychologicalProfile).filter(
        PsychologicalProfile.user_id == current_user.id
    ).first()

    if not user_profile or not user_psych:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your profile and psychological assessment first"
        )

    # Find potential matches
    # 1. Filter by gender preferences
    # 2. Filter by age preferences
    # 3. Exclude already matched users
    # 4. Calculate compatibility for remaining users

    # Get existing match user IDs
    existing_matches = db.query(Match).filter(
        or_(
            Match.user1_id == current_user.id,
            Match.user2_id == current_user.id
        )
    ).all()

    excluded_user_ids = set([current_user.id])
    for match in existing_matches:
        excluded_user_ids.add(match.user1_id)
        excluded_user_ids.add(match.user2_id)

    # Build query for potential matches
    potential_profiles = db.query(UserProfile).filter(
        UserProfile.user_id.notin_(excluded_user_ids),
        UserProfile.is_profile_complete == True,
        UserProfile.gender.in_(user_profile.looking_for_gender)
    ).limit(limit * 2).all()  # Get more than needed for filtering

    matches = []
    for potential_profile in potential_profiles:
        # Get their psychological profile
        potential_psych = db.query(PsychologicalProfile).filter(
            PsychologicalProfile.user_id == potential_profile.user_id
        ).first()

        if not potential_psych:
            continue

        # Calculate compatibility
        compatibility = await ai_service.calculate_compatibility(
            user_psych,
            potential_psych,
            user_profile,
            potential_profile,
            db
        )

        # Only suggest if above threshold
        if compatibility.overall_score >= settings.COMPATIBILITY_THRESHOLD:
            # Create match record
            match = Match(
                user1_id=current_user.id,
                user2_id=potential_profile.user_id,
                status=MatchStatus.PENDING,
                overall_compatibility=compatibility.overall_score,
                personality_compatibility=compatibility.personality_score,
                values_compatibility=compatibility.values_score,
                interests_compatibility=compatibility.interests_score,
                lifestyle_compatibility=compatibility.lifestyle_score,
                compatibility_report=f"Strengths: {', '.join(compatibility.strengths)}. Challenges: {', '.join(compatibility.potential_challenges)}",
                ai_recommendation=compatibility.recommendation
            )
            db.add(match)
            matches.append(match)

            if len(matches) >= limit:
                break

    db.commit()
    return matches[:limit]


@router.get("/", response_model=List[MatchResponse])
async def get_my_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all matches for current user"""

    matches = db.query(Match).filter(
        or_(
            Match.user1_id == current_user.id,
            Match.user2_id == current_user.id
        )
    ).order_by(Match.matched_at.desc()).all()

    return matches


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific match details"""

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    # Verify user is part of this match
    if match.user1_id != current_user.id and match.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this match"
        )

    return match


@router.post("/{match_id}/action", response_model=MatchResponse)
async def match_action(
    match_id: int,
    action: MatchActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform action on a match (accept, reject, start AI mediation)"""

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    # Verify user is part of this match
    if match.user1_id != current_user.id and match.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # Update user interest
    if match.user1_id == current_user.id:
        if action.action == "accept":
            match.user1_interested = True
        elif action.action == "reject":
            match.user1_interested = False
            match.status = MatchStatus.REJECTED
    else:
        if action.action == "accept":
            match.user2_interested = True
        elif action.action == "reject":
            match.user2_interested = False
            match.status = MatchStatus.REJECTED

    # If both users accept, start AI mediation
    if match.user1_interested and match.user2_interested:
        match.status = MatchStatus.AI_MEDIATION
        match.ai_mediation_started_at = datetime.utcnow()

        # Create AI sessions for both users
        session1 = AISession(
            match_id=match.id,
            user_id=match.user1_id,
            status=AISessionStatus.ACTIVE,
            session_data={"qa_pairs": []}
        )
        session2 = AISession(
            match_id=match.id,
            user_id=match.user2_id,
            status=AISessionStatus.ACTIVE,
            session_data={"qa_pairs": []}
        )
        db.add(session1)
        db.add(session2)

    db.commit()
    db.refresh(match)

    return match


@router.get("/{match_id}/ai-session", response_model=AISessionResponse)
async def get_ai_session(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI session for current user in this match"""

    session = db.query(AISession).filter(
        AISession.match_id == match_id,
        AISession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI session not found"
        )

    return session


@router.post("/{match_id}/ai-session/question", response_model=AIQuestionResponse)
async def get_next_question(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get next AI-generated question"""

    session = db.query(AISession).filter(
        AISession.match_id == match_id,
        AISession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI session not found"
        )

    if session.status != AISessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active"
        )

    if session.questions_asked >= settings.AI_QUESTIONS_PER_SESSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All questions have been asked"
        )

    # Get match
    match = db.query(Match).filter(Match.id == match_id).first()

    # Generate question
    question = await ai_service.generate_conversation_question(
        session, current_user, match, db
    )

    # Update session
    session.questions_asked += 1
    session.last_activity_at = datetime.utcnow()
    db.commit()

    return AIQuestionResponse(
        session_id=session.id,
        question=question,
        question_number=session.questions_asked,
        total_questions=settings.AI_QUESTIONS_PER_SESSION
    )


@router.post("/{match_id}/ai-session/response")
async def submit_response(
    match_id: int,
    response_data: AIResponseSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit response to AI question"""

    session = db.query(AISession).filter(
        AISession.match_id == match_id,
        AISession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI session not found"
        )

    # Analyze response
    insight = await ai_service.analyze_conversation_response(
        response_data.question,
        response_data.answer,
        session,
        current_user,
        db
    )

    # Store Q&A pair
    session_data = session.session_data or {"qa_pairs": []}
    session_data["qa_pairs"].append({
        "question": response_data.question,
        "answer": response_data.answer,
        "insight": insight
    })
    session.session_data = session_data
    session.responses_collected += 1
    session.user_insights = insight
    session.last_activity_at = datetime.utcnow()

    # If all questions answered, complete session
    if session.responses_collected >= settings.AI_QUESTIONS_PER_SESSION:
        session.status = AISessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()

        # Check if both users completed their sessions
        match = db.query(Match).filter(Match.id == match_id).first()
        other_user_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
        other_session = db.query(AISession).filter(
            AISession.match_id == match_id,
            AISession.user_id == other_user_id
        ).first()

        if other_session and other_session.status == AISessionStatus.COMPLETED:
            # Both completed - generate final compatibility report
            report = await ai_service.generate_compatibility_report(
                match, session, other_session, db
            )
            match.compatibility_report = report

            # Allow transition to direct chat
            match.status = MatchStatus.ACCEPTED

    db.commit()

    return {
        "message": "Response submitted successfully",
        "insight": insight,
        "session_complete": session.status == AISessionStatus.COMPLETED
    }
