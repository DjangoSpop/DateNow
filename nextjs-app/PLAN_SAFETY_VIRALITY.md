# DateNow: Readiness, Safety, and Virality

## J. Readiness and Compatibility Logic
The **Readiness Engine** determines when a connection is "ready" for direct chat or a meeting.

### Factors
- **Responsiveness**: Time taken to reply, frequency of interaction.
- **Participation Balance**: Each user contributes at least 40% of the conversation.
- **Tone Consistency**: Neutral to positive sentiment, absence of pressure.
- **Values Alignment**: Match between stated values and conversation themes.
- **Emotional Pacing**: Agreement on the speed of the relationship.
- **Willingness to Continue**: Both users express explicit curiosity.

### Weights (0-100)
- **Mutual Curiosity**: 30%
- **Communication Quality**: 25%
- **Values Alignment**: 20%
- **Emotional Pacing**: 15%
- **Participation Balance**: 10%

### Classifications
- **90+**: Ready for Safe Public Meeting
- **75-89**: Ready for Direct Chat
- **50-74**: Continue Guided Conversation
- **30-49**: Slow Down / More Discovery Needed
- **<30**: Mismatch Identified Respectfully

### Edge Cases
- **One-Sided Interest**: AI gently encourages the other user to share more or identifies the mismatch.
- **Abrupt Shift in Tone**: AI pauses and asks for a "comfort check."
- **Ghosting**: AI sends a non-pushy re-engagement prompt (e.g., "Your match has shared something thoughtful").

## K. Safety and Ethical Controls
### Hard Rules
- **No Explicit Content**: Zero tolerance for sexual escalation.
- **No Manipulation**: Detecting guilt tactics or pressure.
- **Privacy Protection**: Names and contact info hidden until mutual readiness is confirmed.

### Interventions
- **Redirect**: AI shifts the topic if it becomes too personal too quickly.
- **Boundary Check**: AI asks "Are you comfortable with this topic?" if it detects sensitivity.
- **Safety Pause**: Conversation is paused for 24 hours if a safety flag is triggered.

### Stop Conditions
- **Harassment**: Immediate termination of the session and match.
- **Direct Refusal**: If a user says "I don't want to continue," the AI ends the session gracefully.
- **Inactivity**: Automatic cleanup of sessions after 48 hours of no response.

### Escalation Logic
- Level 1: AI warning (gentle redirection).
- Level 2: Human review (admin notification).
- Level 3: Account suspension (safety team action).

## L. Viral Mechanics Implementation Plan
### Compatibility Reveal
- **Product**: A "Connection Report" generated at the end of a session.
- **Technical**: Server Action fetches analysis from Gemini, renders a dynamic SVG/Image on the fly (e.g., using `satori` and `resvg`).
### Journey Map
- **Product**: A visual "milestone" tracker showing stages unlocked.
- **Technical**: Client component using Framer Motion to animate a "pathway" from Icebreakers to Readiness.
### Themed Invites
- **Product**: "Send an AI-Guided Intro" - specialized links that initiate a moderated chat.
- **Technical**: Next.js route `/invite/[inviteId]` that prefills the match and session state.
### Reputation Badges
- **Product**: "Thoughtful Communicator," "Respectful Listener" - elegant, non-gamey awards.
- **Technical**: Badge logic in the database, displayed on the user's public profile and shareable "Readiness Card."

## M. Analytics Plan
### Funnel Events
- `signup_started`
- `onboarding_completed`
- `first_match_viewed`
- `consent_given`
- `session_started`
- `session_completed`
- `direct_chat_unlocked`

### Activation Events
- `moderator_question_answered`
- `compatibility_report_shared`
- `friend_invited`

### Retention Metrics
- **D1/D7/D30 Retention**: Essential for any consumer app.
- **Session Completion Rate**: % of moderated sessions that reach the "Outcome" stage.
- **Mutual Match Rate**: Effectiveness of the AI matching and moderation.

### Trust and Safety Metrics
- **Safety Flags Triggered**: Number of interventions needed.
- **User Reports**: Reports against matches or the AI itself.
- **Manual Review Rate**: % of sessions requiring human oversight.

## N. MVP Roadmap
### Sprint 1: Foundation (2 weeks)
- Core Next.js architecture and database schema.
- Basic onboarding flow (Psychological questionnaire).
- Match discovery engine (Basic algorithm).
### Sprint 2: The Moderator (2 weeks)
- Gemini API integration for AI moderation.
- WebSocket-based real-time chat UI.
- Initial 3-stage conversation flow (Icebreakers → Values → Reflection).
### Sprint 3: Readiness & Virality (2 weeks)
- Readiness scoring engine and "Connection Reveal" cards.
- Shareable assets and invite system.
- Analytics and initial trust/safety controls.
### Phase 2: Refinement (4+ weeks)
- Advanced "Journey Map" visuals.
- Multi-language support.
- Enhanced safety interventions with human-in-the-loop options.
- Mobile-app companion (using Capacitor or React Native).
