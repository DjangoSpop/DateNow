"""
AI Moderator Service - Podcast Host Style
Acts as a professional moderator for conversations between matches
"""
import google.generativeai as genai
from typing import Dict, List, Optional, AsyncGenerator
import asyncio
from datetime import datetime
import json

from app.config import settings
from app.models import Match, User, UserProfile, PsychologicalProfile
from sqlalchemy.orm import Session


# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


class AIModerator:
    """
    Professional AI Moderator that facilitates conversations between matches
    Acts like a podcast host - warm, engaging, insightful
    """

    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.generation_config = {
            'temperature': 0.8,  # Higher for more conversational
            'max_output_tokens': 2048,
        }

    def _get_moderator_system_prompt(
        self,
        user1_name: str,
        user2_name: str,
        compatibility_score: float,
        session_context: Dict
    ) -> str:
        """Generate system prompt for AI moderator"""
        return f"""You are a professional dating conversation moderator on DateNow, the world's top AI-powered dating platform.

Your role is like a warm, insightful podcast host facilitating a conversation between two people who might be compatible.

PARTICIPANTS:
- {user1_name} (Person A)
- {user2_name} (Person B)
- Compatibility Score: {compatibility_score:.0%}

YOUR STYLE:
✓ Warm and professional, like a friendly podcast host
✓ Ask thoughtful questions that reveal personality and values
✓ Make insightful observations about their responses
✓ Create a comfortable, authentic atmosphere
✓ Encourage deeper conversation beyond small talk
✓ Notice connections and commonalities
✓ Be genuinely curious and engaged

YOUR RESPONSIBILITIES:
1. Ask ONE person a question at a time (alternate between them)
2. Acknowledge and build on their responses
3. Make brief observations when you notice compatibility
4. Guide the conversation to meaningful topics
5. Keep it balanced - equal time for both
6. Maintain a positive, supportive tone

CONVERSATION FLOW:
- Start with lighter questions to build comfort
- Gradually move to deeper topics (values, life goals, passions)
- Make occasional observations: "I notice you both value..."
- End each turn by directing attention to the next person

RULES:
- NEVER answer for the participants
- NEVER make them both answer the same question simultaneously
- Keep your responses concise (2-3 sentences max)
- One question per response
- Always indicate who should respond: "@{user1_name}" or "@{user2_name}"

CURRENT CONVERSATION STAGE: {session_context.get('stage', 'opening')}
QUESTIONS ASKED SO FAR: {session_context.get('questions_count', 0)}

Remember: Your goal is to help them discover if they're truly compatible through authentic conversation."""

    async def start_conversation(
        self,
        match: Match,
        user1: User,
        user2: User,
        user1_profile: UserProfile,
        user2_profile: UserProfile,
        db: Session
    ) -> str:
        """Generate opening message for the conversation"""

        prompt = f"""Start a conversation between {user1_profile.first_name} and {user2_profile.first_name}.

They matched with {match.overall_compatibility:.0%} compatibility.

Create a warm, welcoming opening (2-3 sentences) that:
1. Greets them both warmly
2. Explains your role as their conversation moderator
3. Sets a positive, comfortable tone
4. Asks the FIRST question to ONE of them (alternate randomly)

Format your response as:
[Your opening greeting]

@{user1_profile.first_name} or @{user2_profile.first_name}: [Your first question]"""

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text.strip()

    async def process_user_response(
        self,
        user_response: str,
        responding_user_name: str,
        other_user_name: str,
        conversation_history: List[Dict],
        session_context: Dict,
        db: Session
    ) -> str:
        """Process user response and generate next moderator message"""

        # Build conversation context
        recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history

        history_text = "\n".join([
            f"{'AI Moderator' if msg['role'] == 'moderator' else msg.get('user_name', 'User')}: {msg['content']}"
            for msg in recent_history
        ])

        prompt = f"""Continue moderating the conversation.

RECENT CONVERSATION:
{history_text}

{responding_user_name} just responded: "{user_response}"

Generate your next response as the moderator:
1. Acknowledge their response briefly (1 sentence)
2. Make an insightful observation if relevant
3. Ask the NEXT question to the OTHER person: @{other_user_name}

Keep it concise and engaging. This is question {session_context.get('questions_count', 0) + 1}/10."""

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text.strip()

    async def generate_streaming_response(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from Gemini (for real-time effect)"""
        try:
            # Gemini streaming
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config,
                stream=True
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    await asyncio.sleep(0.05)  # Smooth streaming effect

        except Exception as e:
            print(f"Streaming error: {e}")
            yield "I apologize, but I'm having trouble responding. Let's continue..."

    async def generate_conversation_summary(
        self,
        conversation_history: List[Dict],
        user1_name: str,
        user2_name: str,
        compatibility_score: float,
        db: Session
    ) -> Dict[str, any]:
        """Generate final summary and recommendation after conversation"""

        history_text = "\n".join([
            f"{msg.get('user_name', 'AI Moderator')}: {msg['content']}"
            for msg in conversation_history
        ])

        prompt = f"""Analyze this AI-moderated conversation between {user1_name} and {user2_name}.

Initial Compatibility Score: {compatibility_score:.0%}

CONVERSATION:
{history_text}

Provide a JSON response with:
{{
    "updated_compatibility": <0-100>,
    "key_connections": ["connection1", "connection2", "connection3"],
    "potential_challenges": ["challenge1", "challenge2"],
    "conversation_highlights": ["highlight1", "highlight2"],
    "recommendation": "proceed" or "reconsider",
    "moderator_notes": "Brief summary of what you observed",
    "suggested_first_date": "A specific first date idea based on their conversation"
}}"""

        response = self.model.generate_content(prompt, generation_config=self.generation_config)

        try:
            # Parse JSON from response
            result_text = response.text.strip()
            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            return json.loads(result_text.strip())
        except:
            # Fallback
            return {
                "updated_compatibility": compatibility_score * 100,
                "key_connections": ["Shared interests", "Similar values"],
                "potential_challenges": ["Communication styles may differ"],
                "conversation_highlights": ["Good rapport", "Authentic responses"],
                "recommendation": "proceed",
                "moderator_notes": "The conversation showed promising compatibility.",
                "suggested_first_date": "Coffee at a cozy café to continue getting to know each other"
            }

    async def generate_icebreaker_question(
        self,
        topic: str,
        user_name: str,
        context: Dict
    ) -> str:
        """Generate a specific icebreaker question"""

        prompt = f"""Generate ONE engaging icebreaker question about {topic} for {user_name}.

Make it:
- Open-ended and thought-provoking
- Reveals personality or values
- Easy to answer authentically
- Conversational, not interview-like

Format: @{user_name}: [your question]"""

        response = self.model.generate_content(prompt, generation_config=self.generation_config)
        return response.text.strip()

    async def detect_conversation_readiness(
        self,
        conversation_history: List[Dict],
        questions_asked: int
    ) -> bool:
        """Detect if conversation has sufficient depth to make a decision"""

        if questions_asked < 8:
            return False

        if len(conversation_history) < 16:  # At least 8 Q&A pairs
            return False

        return True

    async def generate_insight(
        self,
        conversation_snippet: str,
        insight_type: str = "connection"
    ) -> Optional[str]:
        """Generate real-time insight during conversation"""

        if insight_type == "connection":
            prompt = f"""Based on this conversation snippet, make ONE brief observation about a connection or commonality (1 sentence):

"{conversation_snippet}"

Make it warm and encouraging."""

        elif insight_type == "depth":
            prompt = f"""Based on this response, make ONE brief observation about the depth/authenticity (1 sentence):

"{conversation_snippet}"

Be supportive and insightful."""

        else:
            return None

        response = self.model.generate_content(prompt, generation_config={'temperature': 0.7, 'max_output_tokens': 100})
        return response.text.strip()


# Global moderator instance
moderator = AIModerator()
