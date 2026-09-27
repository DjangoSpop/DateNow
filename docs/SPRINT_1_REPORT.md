# SPRINT 1 REPORT — Stabilize the Platform + Create the Mobile Application

- Baseline commit: `1103f21` (HEAD at sprint start; working tree was clean, no uncommitted work to protect)
- Sprint branch: `claude/eloquent-galileo-wjxnki`
- Date: 2026-09-27
- Execution: orchestrator + integration (Agent E) with parallel agents in isolated git worktrees:
  A Backend/Domain, B Mobile, C Questionnaire, D Security (read-only audit). Disjoint file
  ownership; the draft API contract was committed before fan-out and every agent built against it.

## Definition of Done

| Requirement | Status | Evidence |
|---|---|---|
| Backend starts | ✅ | uvicorn against PostgreSQL 16 after `alembic upgrade head`; `/health` 200 |
| DB migrations exist | ✅ | `backend/alembic/versions/0001_initial_schema.py`; `alembic check` shows no drift; upgrade→downgrade→upgrade tested on SQLite + Postgres |
| Authentication works | ✅ | register / login / refresh / `/auth/me`; 30+ token tests |
| Authorization regression tests exist | ✅ | `backend/tests/security/`, `tests/api/*` (IDOR, mass assignment, token confusion, alg none, …) |
| Mobile app builds | ✅ | `tsc --noEmit` 0 errors; `expo lint` clean; `expo export --platform android` and `ios` succeed |
| Register/login work from mobile | ✅ | Live test drives the app's real API client + auth store against the running backend |
| Tokens persist securely | ✅ | `expo-secure-store` only; live test asserts exactly the two token keys are in the secure store and none elsewhere |
| Profile persists | ✅ | Live test: created, then read back after simulated restart |
| Onboarding persists | ✅ | Server-side drafts (`PUT /onboarding`) + local unsynced mirror; resumed after restart |
| Questionnaire scoring server-side | ✅ | `POST /questionnaire/submit` takes raw answers only; client scores rejected (422) |
| App state restores after restart | ✅ | Live test simulates 4 cold restarts (`jest.resetModules`; only the secure store survives) and routes correctly each time |
| TypeScript passes | ✅ | mobile and web frontend both pass `tsc --noEmit` |
| Backend tests pass | ✅ | 306 passed on SQLite and on PostgreSQL 16 |

**Caveat:** the mobile UI was not run on a simulator or physical device in this environment
(no emulator available). Screen navigation and forms are verified by type checking, unit tests,
bundle builds, and the live flow through the same store and routing logic the screens use, not by rendering.
A manual device pass is the first item for Sprint 2 (see *Manual testing*).

## Changes

### Backend (Agent A + integration)
- **Fatal defects fixed (each reproduced first):**
  1. `Message.metadata` is reserved by SQLAlchemy Declarative, so `import app.models` failed. Now
     `message_metadata = Column("metadata", JSON)`; the API field is still `metadata`.
  2. Invalid relationship `UserProfile.interests`: the secondary table keyed by `users.id` had no FK
     path to `user_profiles`, raising `NoForeignKeysError` in `configure_mappers()`. Fixed with
     explicit primary/secondary joins; the association table now has a composite PK and CASCADE.
  3. JWT: tokens were issued with an integer `sub`. python-jose rejects that, so **every**
     authenticated call returned 401. Now `sub` is a string, and `iat`/`exp`/`sub`/`type` are
     required. HS256 is pinned, access vs refresh type is enforced, and a missing header gives 401.
- `create_all` removed from startup; Alembic owns the schema (`init_db()` now runs `alembic upgrade head`,
  used by `seed_data.py`). docker-compose runs migrations before uvicorn.
- `/auth/refresh` implemented (was a stub; token now in the JSON body only). `/auth/me` added.
  Registration persists first/last name. Emails are lower-cased and unique, enforced by a DB CHECK.
  Duplicate registration returns 409.
- Profile: strict schemas (`extra="forbid"`), 18+ check, age-range and field-length validation,
  merged-PATCH validation, lat/long never returned.
- Hardening: `GEMINI_API_KEY` optional with lazy AI init. `DEBUG` defaults to off, with a separate
  `SQL_ECHO`. CORS `*` is rejected. `/docs` is disabled in production. Production refuses weak or
  placeholder JWT secrets, and docker-compose no longer falls back to a default secret. Login runs
  a dummy bcrypt check (no timing oracle). Passwords are 8–128 characters. Login and register have
  an in-process rate limit (429). 422 responses no longer echo submitted values.
- Matches (prototype) IDOR: non-participants now get 404; repeated "accept" no longer duplicates AI sessions.

### Questionnaire (Agent C + integration)
- New server-side catalog `app/questionnaire_catalog.py` (v2026.1, 73 questions, 8 sections).
  It is the single source of truth for questions, options, keying and validation.
- Processor refactored in place (`app/questionnaire_processor.py`). Audit fixes:
  - Scaling: all-1s used to score 20 → now `(mean−1)/4·100`.
  - Missing answers used to score 0.0 → now reported as missing.
  - No type or range checks (e.g. `True` counted as 1; an answer of 100 gave about 2000).
  - Attachment style could never be `anxious` / `fearful-avoidant`, and ignored att_1–4.
  - Free-text `comm_1` was stored verbatim → now a fixed vocabulary.
  - `.lower()` crashed on non-strings.
  - val_7, comm_3, att_3 and att_4 were unused.
- Items are IPIP-50 Big-Five markers, not "BFI-44" (6 items omitted, documented). Reverse keying
  matched the published IPIP keying and the UI; this is verified by tests.
- New endpoints (integration): `GET /questionnaire`, `GET|PUT /onboarding`, `POST /questionnaire/submit`.
  Removed `POST /users/me/psychological-profile` (it accepted client-computed scores).
  Onboarding makes **no AI calls**, so no questionnaire data is sent to Gemini in Sprint 1.

### Mobile (Agent B + integration) — `mobile/`
- Expo SDK 57, React Native 0.86, expo-router, TypeScript strict, zustand.
- Boot/splash screen with `resolveBootRoute`, which picks auth / profile-setup / onboarding / home;
  route guards; a retry screen on network failure that keeps the session.
- Login, register, logout (clears secure store, memory and local drafts).
- Centralized API client:
  - config per environment (production requires https; the Android emulator uses `10.0.2.2`)
  - timeouts via AbortController and a Bearer header
  - structured `ApiError` that parses both 422 shapes
  - single-flight refresh on 401, retried once; a failed refresh returns the user to login
- Profile setup form with field-level server errors. Onboarding is fully server-driven, section by
  section, with progress indicator, debounced draft saves plus save on section change, a local
  unsynced mirror for offline use, resume, and a review/submit step that jumps to the first
  invalid section on 422.
- Home screen shows the server-computed profile summary.

### Web frontend (integration) — `frontend/`
- Root cause of "missing `src/lib/api.ts`": the root `.gitignore` rule `lib/` ignored it. The rule is
  now anchored to `/backend/lib/`, and `api.ts` was added (axios, refresh, timeout).
- TypeScript errors fixed; `tsc` and `vite build` pass. The session is validated via `/auth/me`
  on load. Tokens are no longer in `localStorage`; they are kept in `sessionStorage` (see Known issues).

## Files (100 files changed vs `1103f21`)
- Backend: `app/{models,database,config,auth,main,schemas,ai_service,ai_moderator}.py`,
  `app/routes/{auth,users,matches,onboarding}.py`, `app/questionnaire_{catalog,processor}.py`,
  `alembic.ini`, `alembic/**`, `pytest.ini`, `requirements{,-dev}.txt`, `.env.example`, `Dockerfile`,
  `README_TESTING.md`, `tests/{conftest.py,api,security,db,unit}/**`
- Mobile: all of `mobile/` (`src/app`, `src/api`, `src/auth`, `src/state`, `src/navigation`,
  `src/onboarding`, `src/utils`, `src/components`, `src/config`, `__tests__`, `app.config.ts`, `README.md`)
- Frontend: `src/lib/api.ts`, `src/vite-env.d.ts`, `src/store/authStore.ts`, 4 pages, `package-lock.json`
- Root: `.gitignore`, `docker-compose.yml`, `README.md`, `docs/API_CONTRACT.md`, `docs/SPRINT_1_REPORT.md`

## Migrations
- `0001_initial_schema`: all existing tables, plus:
  - `onboarding_progress` (one row per user; status CHECK; JSON draft answers; questionnaire version; timestamps)
  - `users.first_name` and `users.last_name`; `users.email` lower-case CHECK
  - `psychological_profiles.questionnaire_version`
  - `user_profiles.date_of_birth` is now `DATE`
  - CASCADE / SET NULL on user-owned FKs; a naming convention for constraints
- Enum types are created and dropped correctly on Postgres. Round-trip is tested.

## API changes
The full contract is in `docs/API_CONTRACT.md` (final for Sprint 1). Summary:
- **New:** `POST /auth/refresh` (JSON body), `GET /auth/me`, `GET /questionnaire`, `GET|PUT /onboarding`,
  `POST /questionnaire/submit`
- **Changed:**
  - duplicate registration is 409 (was 400)
  - a missing token is 401 (was 403)
  - strict request bodies (422 on unknown fields)
  - the psychological-profile GET no longer returns `id`, `user_id` or `ai_insights`
  - new 429 status
- **Removed:** `POST /users/me/psychological-profile` (now 405)

## Test results (final run on the integrated branch)

| Suite | Result |
|---|---|
| Backend, SQLite | **306 passed** |
| Backend, PostgreSQL 16 | **306 passed** |
| Backend `alembic check` | no drift |
| Backend `pyflakes` (new/changed modules and tests) | clean |
| Mobile `tsc --noEmit` | 0 errors |
| Mobile `expo lint` | 0 errors / 0 warnings |
| Mobile jest (unit) | 46 passed |
| Mobile live vertical slice (`E2E_API_URL=… npx jest`) | **passed** against uvicorn + Postgres |
| Mobile `expo export` android / ios | success |
| Mobile `expo-doctor` | 19/21; the 2 failures are only because the sandbox network blocks `api.expo.dev` / `reactnative.directory` |
| Web `tsc --noEmit` + `vite build` | pass |

The live vertical slice ran this sequence against the server, with every status as expected:
1. `POST /auth/register` 201, then a restart restores the session (still on profile setup)
2. logout, then `POST /auth/login` 200
3. `POST /users/me/profile` 201, `GET /questionnaire` 200, `PUT /onboarding` 200 (partial draft)
4. restart, `GET /onboarding` 200 with the saved answers and section intact
5. `POST /questionnaire/submit` 201
6. restart lands on home with profile and scores restored
7. with a corrupted access token, a restart gives `GET /auth/me` 401, then `POST /auth/refresh` 200 and a retry 200

## Security findings (Agent D audit; secrets reported by type and location only)
- **Secrets:** no real API keys, private keys or tokens anywhere in the tree or git history. Only placeholders.
  - The dev DB password `datn…` in `docker-compose.yml` / `.env.example` is a dev-only default.
  - The JWT secret fallback in `docker-compose.yml` was a real risk (anyone could forge tokens); it is removed.
- **Fixed in Sprint 1:**
  - CRITICAL: int `sub` broke all auth; refresh tokens were accepted as access tokens; forgeable default secret;
    client-computed psychological scores accepted as authoritative
  - HIGH: refresh stub taking its token in the query string; weak profile validation / mass assignment;
    no auth rate limit; `lib/` gitignore hiding `api.ts`
  - MEDIUM: email case duplicates and login timing oracle; SQL echo tied to DEBUG; localStorage tokens
    in the web client; 422 bodies echoing input
  - LOW: CORS wildcard guard, production docs exposure, HS256 pinned
- **Deferred (outside Sprint 1 scope, in prototype code for Sprints 3–4):**
  - WebSocket: token passed in the query string, no `is_active` check, session looked up by user
    rather than match, no match-state gate, names leaked in broadcasts
  - `GET /matches/suggestions` writes rows on a GET, is one-sided, has an unbounded limit and makes
    synchronous Gemini calls
  - The match compatibility report exposes inferences from the other user's private answers
  - `AIConversationLog` stores full prompts indefinitely
  - Blocking Gemini calls inside async handlers

## Known issues
1. **Mobile UI not exercised on a device or simulator** in this environment (see Manual testing). The DOB field is
   text (`YYYY-MM-DD`), with no native picker. No profile edit screen, no photos, no questionnaire re-take.
2. **Web client** (`frontend/`) still uses its own hard-coded questionnaire with the old 20–100 scale formula, and
   its onboarding pages are not wired to the new endpoints. Tokens are in `sessionStorage` (readable by
   injected scripts); cookie-based web sessions are planned. It is kept as a design and product reference.
3. **No server-side token revocation**: logout is local; refresh tokens are valid until they expire (7 days).
   Rotation and a revocation list are planned with Redis.
4. **Rate limiter is in-process** and keyed on the direct peer IP. It needs Redis for multiple workers and a
   trusted-proxy configuration behind a load balancer.
5. **AI moderator / WebSocket** raise a clear error when `GEMINI_API_KEY` is unset (the matching/chat
   prototype is not usable without a key). Sprint 2 introduces the provider abstraction with fallbacks.
6. Questionnaire:
   - The val_7 weighting into `adventure_seeking` is a heuristic, not a validated scale.
   - The verification text's 20-character minimum shown in the UI is not enforced server-side
     (`verify_authenticity` stays advisory).
   - All 73 questions are required.
7. Environment note: the sandbox's system `cryptography` package was broken and was reinstalled locally.
   Clean virtualenvs from `requirements.txt` are unaffected.

## Manual testing
Performed:
- curl walkthrough (register, duplicate, login, bad password, me, profile CRUD, mass assignment, refresh,
  token confusion, removed endpoint) against uvicorn + Postgres
- the live mobile-client flow above
- Android and iOS JS bundle exports

Still to do on a device before calling the mobile UX verified. Checklist, per `mobile/README.md`:
1. `docker compose up postgres redis backend` (set `JWT_SECRET_KEY`), then `cd mobile && npx expo start`.
2. iOS simulator / Android emulator: register → profile form (try under-18 and min > max) → answer 2 sections →
   kill the app → reopen and confirm it resumes at the saved section → finish → confirm the home screen shows scores.
3. Airplane mode mid-onboarding: answers are kept locally and sync when the network returns.
4. Logout → login → home directly. Reinstalling the app clears the session.

## Next sprint readiness
**Ready for Sprint 2**, with these carry-overs:
- device smoke test of the mobile app (above)
- decide whether `frontend/` gets wired to the new endpoints or frozen as a reference
- Sprint 2 builds the compatibility-profile domain on top of `PsychologicalProfile` + `OnboardingProgress`.
  The questionnaire catalog is versioned (`2026.1`), so new onboarding sections can be added as a new
  version without breaking stored answers.
- the AI provider abstraction replaces the direct Gemini coupling in `ai_service.py` / `ai_moderator.py`

Sprint 2 has **not** been started.
