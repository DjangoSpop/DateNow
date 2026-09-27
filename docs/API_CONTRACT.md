# DateNow API Contract — Sprint 1

> Status: **FINAL for Sprint 1**. Verified by the backend test suite
> (`backend/tests/api`, `backend/tests/security`) and by the live mobile vertical-slice test
> (`mobile/__tests__/e2e.live.test.ts`). Changing it requires updating both.

Base URL: `{API_BASE}/api/v1` (dev: `http://localhost:8000/api/v1`; Android emulator:
`http://10.0.2.2:8000/api/v1`). Production clients must use `https://`.
All bodies are JSON. Authenticated endpoints require `Authorization: Bearer <access_token>`.

All request bodies are **strict**: unknown fields are rejected with 422 (`extra="forbid"`).
This is what prevents mass assignment of server-controlled fields.

## Errors

| Status | Body | Meaning |
|---|---|---|
| 400 | `{"detail": "<message>"}` | Business-rule violation (e.g. profile already exists) |
| 401 | `{"detail": "<message>"}` + `WWW-Authenticate: Bearer` | Missing / malformed / expired / tampered / wrong-type token, unknown user, bad credentials |
| 403 | `{"detail": "Inactive user"}` | Account deactivated (also returned by login and refresh) |
| 404 | `{"detail": "<message>"}` | Resource missing (for `/me` resources: not yet created) |
| 405 | | Method not allowed (e.g. the removed `POST /users/me/psychological-profile`) |
| 409 | `{"detail": "<message>"}` | Duplicate registration; onboarding already completed |
| 422 | `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` | Request validation failure (FastAPI standard) |
| 422 | `{"detail": [{"question_id": "bf_3", "message": "..."}]}` | Questionnaire answer validation (`PUT /onboarding`, `POST /questionnaire/submit`); `question_id` is `"__all__"` for whole-body errors |
| 429 | `{"detail": "..."}` + `Retry-After` | Auth rate limit exceeded (`/auth/login`, `/auth/register`) |

Client rule: on **401** from an authenticated endpoint (other than login/register/refresh),
call `POST /auth/refresh` once (single-flight) and retry once; if refresh returns 401/403,
clear the session and return to login. Network failures during refresh keep the session.

## Tokens

- JWT, HS256 only (pinned server-side). Claims: `sub` (user id **as string**), `exp`, `iat`,
  `type` (`access` | `refresh`). All four are required.
- Access token lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30).
- Refresh token lifetime: `REFRESH_TOKEN_EXPIRE_DAYS` (default 7).
- A refresh token is **not** accepted as an access token and vice versa.
- There is no server-side revocation in Sprint 1: logout is client-side (tokens deleted from
  secure storage). Revocation / rotation lists are planned with Redis.

`Token` response:
```json
{ "access_token": "…", "refresh_token": "…", "token_type": "bearer" }
```

## Auth

### `POST /auth/register` → 201 `Token`
```json
{ "email": "a@b.com", "password": "8–128 chars", "first_name": "Ada (1–50)", "last_name": "optional, ≤50" }
```
409 `Email already registered` (case-insensitive; emails are stored lower-cased). 422 on invalid
input or unknown fields (e.g. `is_verified`). 429 when rate-limited.

### `POST /auth/login` → 200 `Token`
```json
{ "email": "a@b.com", "password": "…" }
```
401 `Incorrect email or password` for unknown email **and** bad password (constant-time-ish:
a dummy hash is checked for unknown emails). 403 for inactive users. 429 when rate-limited.

### `POST /auth/refresh` → 200 `Token`
```json
{ "refresh_token": "…" }
```
Returns a new access **and** refresh token. 401 if invalid/expired/not a refresh token or user
deleted; 403 if inactive. The token is only accepted in the JSON body (never the query string).

### `GET /auth/me` → 200 `Me`
```json
{
  "id": 1, "email": "a@b.com", "first_name": "Ada", "last_name": "L" | null,
  "is_active": true, "is_verified": false, "created_at": "ISO-8601",
  "has_profile": false,
  "onboarding_status": "not_started" | "in_progress" | "completed"
}
```
The single call the mobile app makes on boot to restore state.

## Profile (owner-only; no endpoint reads another user's profile in Sprint 1)

### `GET /users/me/profile` → 200 `Profile` | 404
### `POST /users/me/profile` → 201 `Profile` | 400 if it already exists
```json
{
  "first_name": "Ada", "last_name": "L",
  "date_of_birth": "1995-04-12",
  "gender": "male" | "female" | "non_binary" | "other",
  "bio": "≤1000", "city": "≤100", "country": "≤100", "height_cm": 50–300,
  "looking_for_gender": ["female"],
  "age_preference_min": 25, "age_preference_max": 35,
  "distance_preference_km": 1–500 (default 50),
  "relationship_goal": "serious" | "casual" | "friendship" | "unsure"
}
```
Required: `first_name`, `date_of_birth`, `gender`, `looking_for_gender` (1–4 unique values),
`age_preference_min`, `age_preference_max`, `relationship_goal`.
Server rules: the user must be **18+** (and ≤120, not in the future) → 422 with
`loc: ["body", "date_of_birth"]`; `18 ≤ age_preference_min ≤ age_preference_max ≤ 100`.
Server-controlled fields (`id`, `user_id`, `is_profile_complete`, `photos`, `profile_photo_url`,
`created_at`, `updated_at`, `latitude`, `longitude`) are rejected with 422.

### `PATCH /users/me/profile` → 200 `Profile` | 404
All create fields optional; the same validation applies to fields that are sent, and the merged
result must still satisfy the cross-field rules (18+, min ≤ max). Setting a required field to
`null` → 422. Unknown / server-controlled fields → 422.

`Profile` response = create fields + `id`, `user_id`, `is_profile_complete`, `photos`,
`profile_photo_url`, `created_at`, `updated_at`. Latitude/longitude are never returned.

## Questionnaire / Onboarding

The **server** owns the question catalog (`backend/app/questionnaire_catalog.py`) and all
scoring (`backend/app/questionnaire_processor.py`). Clients submit raw answers only.

Answer value types: `scale` → integer within `scale.min..scale.max` (1–5; booleans and
non-integral numbers rejected); `single_choice` → exactly one of `options`; `multiple_choice`
→ list of unique `options`; `text` → string ≤ `max_length` (1000), no control characters
other than newlines. At most 200 answer keys per request.

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
Version `2026.1`: sections `personality` (44), `values` (7), `love` (5), `communication` (3),
`attachment` (5), `goals` (2), `preferences` (5), `verification` (2) — 73 questions, all
required. Reverse-scoring keys and trait mappings are **not** exposed.

### `GET /onboarding` → 200 `OnboardingState`
```json
{
  "status": "not_started" | "in_progress" | "completed",
  "current_section": "personality" | null,
  "answers": { "bf_1": 4, "comm_1": "Direct and straightforward" },
  "questionnaire_version": "2026.1",
  "updated_at": "ISO-8601" | null,
  "completed_at": "ISO-8601" | null
}
```
Returns `not_started` with empty answers if nothing was saved yet (never 404).

### `PUT /onboarding` → 200 `OnboardingState`
Save a draft (resume support).
```json
{ "current_section": "values", "answers": { "bf_1": 4, "val_1": 5, "bf_2": null } }
```
- `answers` is **merged** into the saved draft; a `null` value removes that saved answer.
- Each provided answer is validated against the catalog: unknown question id / wrong type /
  out of range → 422 (question-id shape), nothing is saved.
- `current_section` must be one of the catalog's section ids (422 otherwise); omit it to keep
  the saved value. Clients on the final review step send the last section's id.
- Sets `status` to `in_progress`. 409 if onboarding is already `completed`.

### `POST /questionnaire/submit` → 201 `PsychologicalProfile`
```json
{ "answers": { "bf_1": 4, "...": "..." } }
```
The server merges `answers` over the saved draft, requires **every required question**
(blank text counts as missing), validates, runs the questionnaire processor, persists the
`PsychologicalProfile` and the final answers, and marks onboarding `completed`.
422 lists every missing/invalid question id. 409 if already completed.
Client-supplied computed fields are rejected: top-level (e.g. `"openness": 99`) → 422 standard
shape; inside `answers` → 422 as an unknown question id.

### `GET /users/me/psychological-profile` → 200 `PsychologicalProfile` | 404
```json
{
  "openness": 0-100, "conscientiousness": 0-100, "extraversion": 0-100,
  "agreeableness": 0-100, "neuroticism": 0-100,
  "family_orientation": 0-100, "career_ambition": 0-100, "adventure_seeking": 0-100,
  "social_consciousness": 0-100, "spiritual_religious": 0-100,
  "communication_style": "direct" | "diplomatic" | "emotional" | "logical",
  "conflict_resolution": "direct" | "reflective" | "collaborative" | "avoidant",
  "love_language_words": 0-100, "love_language_acts": 0-100, "love_language_gifts": 0-100,
  "love_language_time": 0-100, "love_language_touch": 0-100,
  "attachment_style": "secure" | "anxious" | "avoidant" | "fearful-avoidant",
  "questionnaire_version": "2026.1",
  "created_at": "ISO-8601", "updated_at": "ISO-8601" | null
}
```
Scores are 0–100 with one decimal (answer 1 → 0, 5 → 100). Raw questionnaire answers and AI
insight text are never returned here.

**Removed:** `POST /users/me/psychological-profile` (accepted client-computed scores) → 405.

## Health
- `GET /health` (root, **not** under `/api/v1`) → `{ "status": "healthy", ... }`, no auth.

## Out of Sprint 1 scope (pre-existing, not part of this contract)
`/api/v1/matches/*`, `/api/v1/users/interests`, `/api/v1/users/me/interests` and the
`/ws/conversation/{match_id}` WebSocket remain from the prototype. They were only patched for
import/authorization safety (participant checks → 404) and will be redesigned in Sprints 3–4.
