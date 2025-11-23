"""
AI Service for Gemini API integration and conversation management
"""
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.config import settings
from app.models import (
    User, UserProfile, PsychologicalProfile,
    AISession, Match, Message, MessageType,
    AIConversationLog
)
from app.schemas import CompatibilityAnalysis


# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)


class AIService:
    """Service for AI-powered matchmaking and conversation mediation"""

    def __init__(self):
        self.model = genai.GenerativeModel(settings.AI_MODEL)
        self.generation_config = {
            'temperature': settings.AI_TEMPERATURE,
            'max_output_tokens': settings.AI_MAX_TOKENS,
        }

    async def analyze_psychological_profile(
        self,
        profile_data: Dict[str, Any],
        db: Session
    ) -> str:
        """Generate AI insights from psychological profile"""
        prompt = f"""
        As a relationship psychology expert, analyze this psychological profile and provide insights:

        Personality Traits (Big Five):
        - Openness: {profile_data.get('openness')}
        - Conscientiousness: {profile_data.get('conscientiousness')}
        - Extraversion: {profile_data.get('extraversion')}
        - Agreeableness: {profile_data.get('agreeableness')}
        - Neuroticism: {profile_data.get('neuroticism')}

        Values:
        - Family Orientation: {profile_data.get('family_orientation')}
        - Career Ambition: {profile_data.get('career_ambition')}
        - Adventure Seeking: {profile_data.get('adventure_seeking')}
        - Social Consciousness: {profile_data.get('social_consciousness')}
        - Spiritual/Religious: {profile_data.get('spiritual_religious')}

        Communication:
        - Style: {profile_data.get('communication_style')}
        - Conflict Resolution: {profile_data.get('conflict_resolution')}

        Love Languages:
        - Words of Affirmation: {profile_data.get('love_language_words')}
        - Acts of Service: {profile_data.get('love_language_acts')}
        - Gifts: {profile_data.get('love_language_gifts')}
        - Quality Time: {profile_data.get('love_language_time')}
        - Physical Touch: {profile_data.get('love_language_touch')}

        Attachment Style: {profile_data.get('attachment_style')}

        Provide:
        1. A brief personality summary
        2. Relationship strengths
        3. Potential challenges to be aware of
        4. Communication preferences
        5. What they might value in a partner
        """

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text

    async def calculate_compatibility(
        self,
        user1_profile: PsychologicalProfile,
        user2_profile: PsychologicalProfile,
        user1_basic: UserProfile,
        user2_basic: UserProfile,
        db: Session
    ) -> CompatibilityAnalysis:
        """Calculate comprehensive compatibility between two users"""

        # Calculate personality compatibility (Big Five alignment)
        personality_score = self._calculate_personality_compatibility(user1_profile, user2_profile)

        # Calculate values compatibility
        values_score = self._calculate_values_compatibility(user1_profile, user2_profile)

        # Calculate interests compatibility
        interests_score = self._calculate_interests_compatibility(user1_basic, user2_basic)

        # Calculate lifestyle compatibility
        lifestyle_score = self._calculate_lifestyle_compatibility(user1_basic, user2_basic)

        # Overall compatibility (weighted average)
        overall_score = (
            personality_score * 0.3 +
            values_score * 0.3 +
            interests_score * 0.2 +
            lifestyle_score * 0.2
        )

        # Get AI analysis
        prompt = f"""
        As a relationship expert, analyze this compatibility between two people:

        Person 1:
        - Personality: O={user1_profile.openness}, C={user1_profile.conscientiousness}, E={user1_profile.extraversion}, A={user1_profile.agreeableness}, N={user1_profile.neuroticism}
        - Values: Family={user1_profile.family_orientation}, Career={user1_profile.career_ambition}, Adventure={user1_profile.adventure_seeking}
        - Communication: {user1_profile.communication_style}, Conflict: {user1_profile.conflict_resolution}
        - Attachment: {user1_profile.attachment_style}

        Person 2:
        - Personality: O={user2_profile.openness}, C={user2_profile.conscientiousness}, E={user2_profile.extraversion}, A={user2_profile.agreeableness}, N={user2_profile.neuroticism}
        - Values: Family={user2_profile.family_orientation}, Career={user2_profile.career_ambition}, Adventure={user2_profile.adventure_seeking}
        - Communication: {user2_profile.communication_style}, Conflict: {user2_profile.conflict_resolution}
        - Attachment: {user2_profile.attachment_style}

        Compatibility Scores:
        - Personality: {personality_score:.2f}
        - Values: {values_score:.2f}
        - Interests: {interests_score:.2f}
        - Lifestyle: {lifestyle_score:.2f}
        - Overall: {overall_score:.2f}

        Provide:
        1. Three key strengths of this match
        2. Three potential challenges
        3. A recommendation on whether they should proceed with AI-mediated introduction

        Format as JSON with keys: strengths (array), challenges (array), recommendation (string)
        """

        response = self.model.generate_content(prompt, generation_config=self.generation_config)

        # Parse AI response
        try:
            ai_analysis = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        except:
            ai_analysis = {
                "strengths": ["Compatible personalities", "Shared values", "Good communication potential"],
                "challenges": ["May need to work on understanding differences", "Communication styles may vary", "Different backgrounds"],
                "recommendation": "Proceed with AI-mediated introduction to explore compatibility further."
            }

        return CompatibilityAnalysis(
            overall_score=overall_score,
            personality_score=personality_score,
            values_score=values_score,
            interests_score=interests_score,
            lifestyle_score=lifestyle_score,
            strengths=ai_analysis.get("strengths", []),
            potential_challenges=ai_analysis.get("challenges", []),
            recommendation=ai_analysis.get("recommendation", "")
        )

    def _calculate_personality_compatibility(
        self,
        profile1: PsychologicalProfile,
        profile2: PsychologicalProfile
    ) -> float:
        """Calculate Big Five personality compatibility"""
        # Some traits should be similar, others can be complementary
        similarity_traits = ['openness', 'agreeableness', 'conscientiousness']
        complementary_traits = ['extraversion', 'neuroticism']

        scores = []

        # Similarity traits (closer = better)
        for trait in similarity_traits:
            val1 = getattr(profile1, trait)
            val2 = getattr(profile2, trait)
            diff = abs(val1 - val2)
            score = 1 - (diff / 100)  # Convert to 0-1 scale
            scores.append(score)

        # Complementary traits (moderate difference is good)
        for trait in complementary_traits:
            val1 = getattr(profile1, trait)
            val2 = getattr(profile2, trait)
            diff = abs(val1 - val2)
            # Sweet spot is 20-40 points difference
            if 20 <= diff <= 40:
                score = 1.0
            else:
                score = 0.7
            scores.append(score)

        return sum(scores) / len(scores)

    def _calculate_values_compatibility(
        self,
        profile1: PsychologicalProfile,
        profile2: PsychologicalProfile
    ) -> float:
        """Calculate values compatibility"""
        value_traits = [
            'family_orientation',
            'career_ambition',
            'adventure_seeking',
            'social_consciousness',
            'spiritual_religious'
        ]

        scores = []
        for trait in value_traits:
            val1 = getattr(profile1, trait)
            val2 = getattr(profile2, trait)
            diff = abs(val1 - val2)
            score = 1 - (diff / 100)
            scores.append(score)

        return sum(scores) / len(scores)

    def _calculate_interests_compatibility(
        self,
        profile1: UserProfile,
        profile2: UserProfile
    ) -> float:
        """Calculate shared interests compatibility"""
        # This would use the interests relationship
        # Simplified for now
        return 0.75  # Placeholder

    def _calculate_lifestyle_compatibility(
        self,
        profile1: UserProfile,
        profile2: UserProfile
    ) -> float:
        """Calculate lifestyle compatibility based on location, goals, etc."""
        score = 0.0

        # Relationship goal alignment
        if profile1.relationship_goal == profile2.relationship_goal:
            score += 0.5

        # Age preference compatibility
        # Check if each person falls within the other's age range
        # This would require birth date calculations
        score += 0.5  # Placeholder

        return score

    async def generate_conversation_question(
        self,
        session: AISession,
        user: User,
        match: Match,
        db: Session
    ) -> str:
        """Generate a personalized question for AI-mediated conversation"""

        user_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        psych_profile = db.query(PsychologicalProfile).filter(PsychologicalProfile.user_id == user.id).first()

        # Get previous questions and answers from session
        session_data = session.session_data or {}
        previous_qa = session_data.get('qa_pairs', [])

        # Determine which user is the "other" in this match
        other_user_id = match.user2_id if match.user1_id == user.id else match.user1_id
        other_profile = db.query(PsychologicalProfile).filter(
            PsychologicalProfile.user_id == other_user_id
        ).first()

        prompt = f"""
        You are an expert relationship counselor facilitating a conversation between two people who may be compatible.

        User Background:
        - Name: {user_profile.first_name}
        - Gender: {user_profile.gender}
        - Relationship Goal: {user_profile.relationship_goal}
        - Communication Style: {psych_profile.communication_style}
        - Attachment Style: {psych_profile.attachment_style}

        Previous Conversation:
        {json.dumps(previous_qa, indent=2) if previous_qa else "This is the first question"}

        Your goal is to help this person reveal authentic aspects of themselves that would help determine compatibility
        with someone who has {other_profile.communication_style} communication style and values
        {other_profile.attachment_style} attachment.

        Generate ONE thoughtful, open-ended question that:
        1. Builds naturally on previous responses (if any)
        2. Explores values, lifestyle, or emotional intelligence
        3. Is personal but not invasive
        4. Helps assess compatibility
        5. Feels conversational, not like an interview

        Question {session.questions_asked + 1} of {settings.AI_QUESTIONS_PER_SESSION}:
        """

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        question = response.text.strip()

        # Log the interaction
        log = AIConversationLog(
            session_id=str(session.id),
            user_id=user.id,
            prompt=prompt,
            response=question,
            model_used=settings.AI_MODEL,
            tokens_used=len(prompt.split()) + len(question.split())  # Rough estimate
        )
        db.add(log)
        db.commit()

        return question

    async def analyze_conversation_response(
        self,
        question: str,
        answer: str,
        session: AISession,
        user: User,
        db: Session
    ) -> str:
        """Analyze a user's response and generate insights"""

        psych_profile = db.query(PsychologicalProfile).filter(
            PsychologicalProfile.user_id == user.id
        ).first()

        prompt = f"""
        As a relationship psychologist, analyze this response in the context of dating compatibility:

        Question: {question}
        Answer: {answer}

        User's Known Traits:
        - Communication Style: {psych_profile.communication_style}
        - Attachment Style: {psych_profile.attachment_style}
        - Emotional Openness: {psych_profile.openness}

        Provide a brief insight (2-3 sentences) about what this response reveals about:
        1. Their values and priorities
        2. Their emotional availability
        3. Compatibility indicators

        Keep it professional and constructive.
        """

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text.strip()

    async def generate_compatibility_report(
        self,
        match: Match,
        session1: AISession,
        session2: AISession,
        db: Session
    ) -> str:
        """Generate final compatibility report after AI-mediated conversation"""

        user1_data = session1.session_data or {}
        user2_data = session2.session_data or {}

        prompt = f"""
        As a relationship expert, create a compatibility report for two people based on their AI-mediated conversation.

        Person 1 Responses:
        {json.dumps(user1_data.get('qa_pairs', []), indent=2)}

        Person 1 Insights:
        {session1.user_insights}

        Person 2 Responses:
        {json.dumps(user2_data.get('qa_pairs', []), indent=2)}

        Person 2 Insights:
        {session2.user_insights}

        Initial Compatibility Score: {match.overall_compatibility:.2f}

        Based on their authentic responses, provide:
        1. Updated compatibility assessment
        2. Key areas of alignment
        3. Potential challenges to discuss
        4. Recommendation: Should they transition to direct messaging?
        5. Conversation starters if they proceed

        Be honest but constructive. Format as a warm, professional report.
        """

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text.strip()

    async def generate_conversation_starter(
        self,
        match: Match,
        for_user_id: int,
        db: Session
    ) -> str:
        """Generate a personalized conversation starter for direct messaging"""

        # Get both users' profiles
        user1 = db.query(User).filter(User.id == match.user1_id).first()
        user2 = db.query(User).filter(User.id == match.user2_id).first()

        current_user = user1 if for_user_id == match.user1_id else user2
        other_user = user2 if for_user_id == match.user1_id else user1

        current_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        other_profile = db.query(UserProfile).filter(UserProfile.user_id == other_user.id).first()

        prompt = f"""
        Generate a warm, personalized conversation starter for {current_profile.first_name} to send to {other_profile.first_name}.

        Context:
        - They've completed AI-mediated introduction
        - Compatibility score: {match.overall_compatibility:.2f}
        - Shared interests and values have been identified

        Create a natural, friendly opening message that:
        1. References something from their compatibility (without being too specific)
        2. Asks an engaging question
        3. Shows genuine interest
        4. Feels authentic, not scripted

        Keep it brief (2-3 sentences).
        """

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text.strip()


# Global AI service instance
ai_service = AIService()
