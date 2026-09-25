# DateNow API Contract — Sprint 1

Status: **authoritative for Sprint 1.** Backend and mobile both implement exactly this.
Changes go through the integration lead, never unilaterally.

Base URL: `{API_BASE_URL}/api/v1` (dev default `http://localhost:8000`). JSON everywhere, UTF-8.
Auth: `Authorization: Bearer <access_token>` on every endpoint marked 🔒.

## Conventions

### Error envelope
Every non-2xx response has this shape (including validation errors and 404s):

```json
{ "error": { "code": "EMAIL_TAKEN", "message": "Human readable text", "fields": { "email": "already registered" } } }
```

- `code` — stable machine string (list below). Clients branch on `code`, never on `message`.
- `fields` — optional, only on `VALIDATION_ERROR` / `QUESTIONNAIRE_INCOMPLETE`; maps field (or question id) → message.

| HTTP | code | When |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | missing bearer token |
| 401 | `INVALID_TOKEN` | malformed, bad signature, wrong token type, unknown user |
| 401 | `TOKEN_EXPIRED` | valid signature but expired |
| 401 | `INVALID_CREDENTIALS` | login email/password mismatch |
| 403 | `ACCOUNT_DISABLED` | user `is_active = false` |
| 404 | `NOT_FOUND` / `PROFILE_NOT_FOUND` / `PSYCH_PROFILE_NOT_FOUND` | |
| 409 | `EMAIL_TAKEN` | register with existing email (case-insensitive) |
| 409 | `PROFILE_EXISTS` | POST profile when one exists |
| 422 | `VALIDATION_ERROR` | request body/query invalid; `fields` populated |
| 422 | `QUESTIONNAIRE_INCOMPLETE` | submit with required answers missing; `fields` = `{question_id: "required"}` |
| 500 | `INTERNAL_ERROR` | unexpected; no stack traces or internals in body |

Mobile client rule: on `401 TOKEN_EXPIRED` or `INVALID_TOKEN` from a 🔒 endpoint, call `/auth/refresh` **once**, retry the
original request once; if refresh fails, clear stored tokens and route to login.

### Types
- Dates: `YYYY-MM-DD`. Timestamps: ISO-8601 UTC with offset.
- Enums (lowercase strings):
  - `Gender`: `male | female | non_binary | other`
  - `RelationshipGoal`: `serious | casual | friendship | unsure`

## Auth

### `POST /auth/register`
Request `{ "email": "a@b.com", "password": "min 8, max 128 chars" }` → **201** `TokenPair`.
Email is trimmed + lower-cased. Extra fields are ignored. Errors: 409 `EMAIL_TAKEN`, 422.

### `POST /auth/login`
Request `{ "email", "password" }` → **200** `TokenPair`. Errors: 401 `INVALID_CREDENTIALS`, 403 `ACCOUNT_DISABLED`, 422.

### `POST /auth/refresh`
Request `{ "refresh_token": "..." }` → **200** `TokenPair` (new access **and** new refresh token).
Errors: 401 `INVALID_TOKEN` / `TOKEN_EXPIRED` (also when an *access* token is supplied).

`TokenPair`:
```json
{ "access_token": "jwt", "refresh_token": "jwt", "token_type": "bearer", "expires_in": 1800 }
```
JWT claims: `sub` (user id as **string**), `type` (`access` | `refresh`), `iat`, `exp`. Access tokens are rejected where a
refresh token is required and vice versa. Sprint 1 tokens are stateless (no server-side revocation; logout = client discards tokens).

## Current user

### 🔒 `GET /users/me`
**200**
```json
{
  "id": 12, "email": "a@b.com", "is_verified": false, "created_at": "2026-09-25T10:00:00+00:00",
  "onboarding": {
    "profile_complete": true,
    "questionnaire_complete": false,
    "questionnaire_answered": 17,
    "questionnaire_total": 71,
    "questionnaire_version": "ipip-v1",
    "complete": false
  }
}
```
`complete = profile_complete && questionnaire_complete`. The mobile app routes on this object after restore.

## Profile (owner only — there is no endpoint that reads another user's profile in Sprint 1)

### 🔒 `GET /users/me/profile` → **200** `Profile` | 404 `PROFILE_NOT_FOUND`
### 🔒 `POST /users/me/profile` → **201** `Profile` | 409 `PROFILE_EXISTS` | 422
### 🔒 `PATCH /users/me/profile` → **200** `Profile` | 404 | 422 (partial; only fields present are changed)

`ProfileCreate` (POST):
| field | type | rules |
|---|---|---|
| `first_name` | string | required, 1–50, trimmed |
| `last_name` | string? | ≤ 50 |
| `date_of_birth` | date | required; **age ≥ 18** server-side (else 422, `fields.date_of_birth`); not in the future; age ≤ 120 |
| `gender` | Gender | required |
| `looking_for_gender` | Gender[] | required, 1–4 unique values |
| `age_preference_min` | int | required, 18–100 |
| `age_preference_max` | int | required, 18–100, ≥ min |
| `relationship_goal` | RelationshipGoal | required |
| `bio` | string? | ≤ 500 |
| `city`, `country` | string? | ≤ 100 |

`ProfileUpdate` (PATCH): same fields, all optional, same rules (min/max checked against the resulting values).
Unknown fields → 422 (`extra="forbid"`), so server-owned fields (`user_id`, `is_profile_complete`, coordinates, photos) can
never be mass-assigned.

`Profile` response:
```json
{
  "first_name": "Sam", "last_name": null, "date_of_birth": "1995-04-02", "age": 31,
  "gender": "female", "looking_for_gender": ["male"], "age_preference_min": 27, "age_preference_max": 38,
  "relationship_goal": "serious", "bio": null, "city": "Cairo", "country": "Egypt",
  "created_at": "...", "updated_at": "..."
}
```
Never returned: latitude/longitude, internal ids of other users.

## Questionnaire (server-owned question bank; the server alone computes scores)

### 🔒 `GET /questionnaire`
**200**
```json
{
  "version": "ipip-v1",
  "sections": [
    {
      "id": "personality", "title": "Your Personality", "description": "...", "estimated_minutes": 6,
      "questions": [
        { "id": "bf_1", "text": "I am the life of the party", "type": "scale", "required": true,
          "scale": { "min": 1, "max": 5, "labels": { "1": "Strongly Disagree", "5": "Strongly Agree" } } },
        { "id": "comm_1", "text": "...", "type": "single_choice", "required": true,
          "options": [ { "value": "direct", "label": "Direct and straightforward" } ] }
      ]
    }
  ]
}
```
Answer value types: `scale` → integer within `[min, max]`; `single_choice` → one of the option `value` strings.
Section/question order is the presentation order.

### 🔒 `GET /users/me/questionnaire`
**200** `QuestionnaireState`:
```json
{ "version": "ipip-v1", "answers": { "bf_1": 4, "comm_1": "direct" },
  "answered": 2, "total_required": 71, "missing": ["bf_2", "..."], "complete": false, "scored_at": null }
```
`complete` = a psychological profile has been computed from the current answers' version.

### 🔒 `PUT /users/me/questionnaire/answers`
Request `{ "answers": { "bf_1": 4, "bf_2": 2 } }` (1–100 entries) → **200** `QuestionnaireState`.
Merge/upsert: listed answers are created or replaced; others untouched. The whole request is rejected (422, `fields` keyed by
question id) if any id is unknown or any value invalid — nothing is saved in that case. Intended for autosave (per answer or
per section).

### 🔒 `POST /users/me/questionnaire/submit`
No body. Validates all required questions are answered, runs the server-side scorer, creates or replaces the user's
psychological profile. **200** `PsychologicalProfile`. Errors: 422 `QUESTIONNAIRE_INCOMPLETE`.
Resubmitting after changing answers recomputes the profile.

### 🔒 `GET /users/me/psychological-profile` → **200** `PsychologicalProfile` | 404 `PSYCH_PROFILE_NOT_FOUND`

`PsychologicalProfile`:
```json
{
  "questionnaire_version": "ipip-v1", "scored_at": "...",
  "big_five": { "openness": 62.5, "conscientiousness": 71.9, "extraversion": 40.6, "agreeableness": 80.0, "neuroticism": 31.3 },
  "values": { "family_orientation": 75.0, "career_ambition": 50.0, "adventure_seeking": 75.0, "social_consciousness": 50.0, "spiritual_religious": 25.0 },
  "love_languages": { "words": 75.0, "acts": 50.0, "gifts": 25.0, "time": 100.0, "touch": 50.0 },
  "communication_style": "direct", "conflict_resolution": "collaborative", "attachment_style": "secure"
}
```
All numeric scores are 0–100. There is **no** endpoint through which a client can write scores.

## Removed in Sprint 1
- `POST /users/me/psychological-profile` (accepted client-computed scores) — replaced by questionnaire submit.

## Unchanged, out of Sprint 1 scope
`/users/interests`, `/users/me/interests`, `/matches/*`, `/ws/conversation/{match_id}` keep their baseline behaviour,
except the WebSocket now refuses matches that are not in `ai_mediation` (consent hot-fix). They are redesigned in Sprints 3–4.
