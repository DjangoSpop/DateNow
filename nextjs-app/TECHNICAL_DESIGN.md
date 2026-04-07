# DateNow: Technical and Data Design

## G. Data Model Design
### `User`
- `id`: string (UUID)
- `email`: string (unique)
- `hashed_password`: string
- `is_verified`: boolean
- `created_at`: timestamp

### `UserProfile`
- `user_id`: ForeignKey(User)
- `first_name`: string
- `date_of_birth`: date
- `gender`: string
- `bio`: text
- `city`: string
- `photos`: JSON (list of URLs)
- `relationship_goal`: Enum

### `PsychologicalProfile`
- `user_id`: ForeignKey(User)
- `openness`: float (0-100)
- `conscientiousness`: float
- `extraversion`: float
- `agreeableness`: float
- `neuroticism`: float
- `family_orientation`: float
- `career_ambition`: float
- `communication_style`: string (direct, diplomatic, etc.)
- `attachment_style`: string (secure, anxious, etc.)

### `Match`
- `id`: string (UUID)
- `user1_id`: ForeignKey(User)
- `user2_id`: ForeignKey(User)
- `status`: Enum (pending, accepted, ai_mediation, direct_chat, ended)
- `overall_compatibility`: float (0-1)
- `matched_at`: timestamp

### `ModeratedSession`
- `id`: string (UUID)
- `match_id`: ForeignKey(Match)
- `stage`: Enum (consent, icebreakers, values, lifestyle, reflection, readiness, outcome)
- `questions_asked`: int (default 0)
- `max_questions`: int (default 10)
- `started_at`: timestamp
- `last_activity`: timestamp

### `Message`
- `id`: string (UUID)
- `session_id`: ForeignKey(ModeratedSession)
- `sender_id`: ForeignKey(User, nullable=True)
- `message_type`: Enum (moderator, user, system)
- `content`: text
- `created_at`: timestamp

### `ReadinessResult`
- `session_id`: ForeignKey(ModeratedSession, unique)
- `score`: float (0-100)
- `recommendation`: Enum (continue_guided, unlock_direct, suggest_meeting, slow_down, mismatch)
- `moderator_notes`: text
- `compatibility_dimensions`: JSON (values, communication, lifestyle, emotional)

### `ShareCard`
- `id`: string (UUID)
- `user_id`: ForeignKey(User)
- `type`: Enum (compatibility, personality, journey)
- `image_url`: string
- `created_at`: timestamp

### `InviteTracking`
- `id`: string (UUID)
- `inviter_id`: ForeignKey(User)
- `invitee_email`: string
- `status`: Enum (pending, joined, matched)
- `reward_status`: string

## H. Gemini Integration Design
### System Prompt Strategy
- **Role**: Professional Dating Moderator (Calm, Neutral, Respectful).
- **Tone**: Warm, insightful, non-flirtatious, emotionally intelligent.
- **Goal**: Facilitate deep, respectful, balanced discovery between two users.

### Structured Output Format
- Prompting Gemini to return JSON for analysis and structured questions.
- Example JSON:
  ```json
  {
    "moderator_message": "...",
    "question_to": "User1",
    "detected_sentiment": "positive",
    "safety_flag": false,
    "next_stage": "values"
  }
  ```

### Moderation Controls
- Initial prompt includes explicit safety instructions.
- Pre-screening of user input for high-risk keywords before sending to Gemini.
- Post-processing Gemini output for consistency and safety compliance.

### Token & Cost Control
- Using `gemini-1.5-flash` for high-volume moderation tasks.
- Using `gemini-1.5-pro` for deep compatibility analysis and readiness summaries.
- Session-based conversation windowing (summarizing older messages to stay within token limits).

## I. Component and UI System
### Page-by-Page Breakdown
- **Landing**: Animated hero section with value prop and "Start Your Journey" button.
- **Onboarding**: "Psychological Deep Dive" - one question at a time, smooth progress bar, gender-theming.
- **Dashboard**: "Your Connections" - card-based view of matches, each with a "Stage" indicator.
- **Conversation**: "Guided Session" - split screen for desktop, mobile-first messaging UI with a prominent "Moderator" persona.
- **Outcome**: "Connection Reveal" - visual summary of the session, shareable compatibility card.

### Component Tree (Partial)
- `Layout`
  - `Navbar`
  - `Main`
    - `ConversationUI`
      - `ModeratorBubble`
      - `MessageList`
      - `UserMessageBubble`
      - `ActionPanel` (Response input, readiness check)
    - `CompatibilityCard`
      - `ScoreIndicator`
      - `DimensionGrid`
      - `ShareButton`
    - `OnboardingFlow`
      - `ProgressTracker`
      - `QuestionCard`

### Mobile-First Behavior
- Responsive layouts using Tailwind's flex and grid.
- Touch-optimized buttons and inputs (min 44px).
- Smooth transitions for page changes to feel like a native app.

### Premium UI Direction
- **Typography**: Serene, elegant sans-serif (e.g., Inter or Geist).
- **Color Palette**: Calm blues, soft pinks, and warm neutrals.
- **Elevation**: Subtle shadows and glassmorphism for a modern, clean look.
- **Motion**: Framer Motion for gentle entrances and transitions.
