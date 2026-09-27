# DateNow API Contract — Sprint 1

> Status: **DRAFT (orchestrator-owned)**. Agents build against this; the Integration
> step finalizes it. Any deviation must be reported back, not silently changed.

Base URL: `{API_BASE}/api/v1` (dev: `http://localhost:8000/api/v1`).
All bodies are JSON. Authenticated endpoints require `Authorization: Bearer <access_token>`.

## Errors

FastAPI-standard shape:

| Status | Body | Meaning |
|---|---|---|
| 400 | `{"detail": "<message>"}` | Business-rule violation (e.g. profile already exists) |
| 401 | `{"detail": "<message>"}` + `WWW-Authenticate: Bearer` | Missing / malformed / expired / wrong-type token, unknown user |
| 403 | `{"detail": "Inactive user"}` | Authenticated but not allowed |
| 404 | `{"detail": "<message>"}` | Resource missing (for `/me` resources: not yet created) |
| 409 | `{"detail": "Email already registered"}` | Duplicate registration |
| 422 | `{"detail": [ {loc, msg, type}, ... ]}` | Request validation failure |

Clients: on **401** from any authenticated endpoint, attempt one refresh via
`POST /auth/refresh`; if that fails, clear the session and return to login.

## Tokens

- JWT HS256. Claims: `sub` (user id **as string**), `exp`, `iat`, `type` (`access` | `refresh`).
- Access token lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30).
- Refresh token lifetime: `REFRESH_TOKEN_EXPIRE_DAYS` (default 7).
- A refresh token is **not** accepted as an access token and vice versa.

`Token` response:
```json
{ "access_token": "…", "refresh_token": "…", "token_type": "bearer" }
```

## Auth

### `POST /auth/register` → 201 `Token`
```json
{ "email": "a@b.com", "password": "min 8 chars", "first_name": "Ada", "last_name": "L" }
```
409 if email exists (case-insensitive; emails are stored lower-cased). 422 on invalid input.

### `POST /auth/login` → 200 `Token`
```json
{ "email": "a@b.com", "password": "…" }
```
401 `Incorrect email or password` (same message for unknown email and bad password).

### `POST /auth/refresh` → 200 `Token`
```json
{ "refresh_token": "…" }
```
401 if invalid/expired/not a refresh token.

### `GET /auth/me` → 200 `Me`
```json
{
  "id": 1, "email": "a@b.com", "first_name": "Ada", "last_name": "L",
  "is_active": true, "is_verified": false, "created_at": "ISO-8601",
  "has_profile": false,
  "onboarding_status": "not_started" | "in_progress" | "completed"
}
```
This is the single call the mobile app makes on boot to restore state.

## Profile (owner-only; there is no endpoint to read another user's profile in Sprint 1)

### `GET /users/me/profile` → 200 `Profile` | 404
### `POST /users/me/profile` → 201 `Profile` | 400 if exists
```json
{
  "first_name": "Ada", "last_name": "L",
  "date_of_birth": "1995-04-12",
  "gender": "male" | "female" | "non_binary" | "other",
  "bio": "…", "city": "…", "country": "…", "height_cm": 170,
  "looking_for_gender": ["female"],
  "age_preference_min": 25, "age_preference_max": 35,
  "distance_preference_km": 50,
  "relationship_goal": "serious" | "casual" | "friendship" | "unsure"
}
```
Server rules: user must be **18+** (422 otherwise); `age_preference_min <= age_preference_max`, both 18–100.
Server-controlled fields (`id`, `user_id`, `is_profile_complete`, `photos`, `profile_photo_url`,
`created_at`, `updated_at`, lat/long) are **ignored/rejected** if sent (`extra="forbid"` → 422).

### `PATCH /users/me/profile` → 200 `Profile` | 404
All create fields optional; the same validation applies to fields that are sent, and the merged result must still satisfy the cross-field rules (18+, min ≤ max). `extra="forbid"`.

`Profile` response = create fields + `id`, `user_id`, `is_profile_complete`, `photos`, `profile_photo_url`, `created_at`, `updated_at`.
Latitude/longitude are never returned.

## Questionnaire / Onboarding

The **server** owns the question catalog and all scoring. Clients submit raw answers only.

### `GET /questionnaire` → 200 `QuestionnaireDefinition` (auth required)
```json
{
  "version": "2026.1",
  "sections": [
    { "id": "personality", "title": "…", "description": "…",
      "questions": [
        { "id": "bf_1", "text": "I am the life of the party",
          "type": "scale" | "single_choice" | "multiple_choice" | "text",
          "required": true,
          "options": null | ["…"],
          "scale": { "min": 1, "max": 5, "min_label": "Strongly disagree", "max_label": "Strongly agree" } | null,
          "max_length": null | 1000 }
      ] }
  ]
}
```
Reverse-scoring keys and trait mappings are **not** exposed.

### `GET /onboarding` → 200 `OnboardingState`
```json
{
  "status": "not_started" | "in_progress" | "completed",
  "current_section": "personality" | null,
  "answers": { "bf_1": 4, "comm_1": "direct" },
  "questionnaire_version": "2026.1",
  "updated_at": "ISO-8601" | null,
  "completed_at": "ISO-8601" | null
}
```
Returns `not_started` with empty answers if nothing saved yet (never 404).

### `PUT /onboarding` → 200 `OnboardingState`
Save a draft (resume support). Body:
```json
{ "current_section": "values", "answers": { "bf_1": 4, "val_1": 5 } }
```
`answers` is **merged** into the saved draft. Each provided answer is validated against the
catalog (unknown question id / wrong type / out of range → 422). Partial answers allowed.
409 if onboarding is already `completed` (use submit to re-take — out of scope Sprint 1).

### `POST /questionnaire/submit` → 201 `PsychologicalProfile`
```json
{ "answers": { "bf_1": 4, "...": "..." } }
```
Server merges with saved draft, requires **all required questions**, validates, runs the
questionnaire processor, persists the `PsychologicalProfile`, marks onboarding `completed`.
422 lists missing/invalid question ids. 409 if already completed.
Any client-supplied computed field (e.g. `openness`) is rejected (422).

### `GET /users/me/psychological-profile` → 200 `PsychologicalProfile` | 404
```json
{
  "openness": 0-100, "conscientiousness": 0-100, "extraversion": 0-100,
  "agreeableness": 0-100, "neuroticism": 0-100,
  "family_orientation": 0-100, "career_ambition": 0-100, "adventure_seeking": 0-100,
  "social_consciousness": 0-100, "spiritual_religious": 0-100,
  "communication_style": "…", "conflict_resolution": "…",
  "love_language_words": 0-100, "love_language_acts": 0-100, "love_language_gifts": 0-100,
  "love_language_time": 0-100, "love_language_touch": 0-100,
  "attachment_style": "…",
  "questionnaire_version": "2026.1",
  "created_at": "ISO-8601", "updated_at": "ISO-8601" | null
}
```
Raw questionnaire answers and AI insight text are not returned here.

**Removed:** `POST /users/me/psychological-profile` (accepted client-computed scores).

## Health
- `GET /health` → `{ "status": "healthy", ... }` (no auth)
