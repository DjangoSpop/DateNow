# SPRINT 1 REPORT — Stabilise the platform + create the mobile application

Sprint branch: `claude/festive-dijkstra-4g97qv` · Started from `16fcb2c` (assessment) · Baseline code `1103f21`
Status: **DONE** (declared by integration after the complete suite, CI and the live vertical test passed — evidence below).

## Definition of Done

| Requirement | Status | Evidence |
|---|---|---|
| Backend starts | ✅ | `alembic upgrade head && uvicorn app.main:app` → `/health` 200 (local + CI `e2e` job) |
| DB migrations exist | ✅ | Alembic `0001` baseline, `0002` Sprint 1; upgrade → downgrade → upgrade + `alembic check` (no drift) in CI |
| Authentication works | ✅ | register / login / refresh / `GET /users/me`; `tests/test_auth.py`, `tests/security/test_sec_jwt.py` |
| Authorization regression tests exist | ✅ | `tests/security/` (629 tests incl. endpoint-table completeness check) |
| Mobile app builds | ✅ | `npx expo export --platform ios --platform android` (local + CI) |
| Register/login work from mobile | ✅ | Real mobile client code against a live backend: `mobile/src/__e2e__/vertical.e2e.test.ts` |
| Tokens persist securely | ✅ | `expo-secure-store` only (no AsyncStorage); `src/auth/__tests__/tokenStorage.test.ts` |
| Profile persists | ✅ | E2E: created, then read back after cold restart |
| Onboarding persists | ✅ | E2E: 30 answers autosaved, app "killed", resumed at question 31, finished |
| Questionnaire scoring server-side | ✅ | `POST /users/me/questionnaire/submit`; client-score write route removed (405); `tests/test_questionnaire_api.py` |
| App state restores after restart | ✅ | E2E: fresh module load restores session + `onboarding.complete = true`; corrupted token → refresh → restored |
| TypeScript passes | ✅ | `npx tsc --noEmit` (strict + `noUncheckedIndexedAccess`) |
| Backend tests pass | ✅ | **831 passed, 1 xfailed** (strict xfail documents open finding L-4) |

**Not verified in this environment:** running on a physical device, simulator or Expo Go (no device available). Rendering, keyboard
behaviour, screen readers and on-device keychain behaviour are unverified; only bundling, logic and live-API integration are.

## How the sprint was run

The API contract (`docs/API_CONTRACT.md`) was written first so work could proceed in parallel. Four agents in isolated worktrees
with explicit file ownership; integration reviewed, reproduced each agent's claims, merged, and wired the seams.

| Agent | Delivered | Integration verification |
|---|---|---|
| A — Backend | 3 fatal bugs reproduced + fixed, auth/profile contract, error envelope, Alembic, Postgres test suite, WS consent gate | Merged; re-ran suite |
| B — Mobile | Expo SDK 57 app, API client, secure storage, auth/onboarding flow, 50 unit tests | Clean `npm ci` → tsc, lint, jest, export re-run |
| C — Questionnaire | Server-owned `ipip-v1` bank (71 questions), validation, deterministic scorer, audit of old processor | Re-ran 88 tests + spot-checked scoring |
| D — Security/QA | Secret scan, 629 security tests, 3 fixes, review doc | Merged; full suite |
| E — Integration | Questionnaire endpoints + service, E2E test, CI, H-1 fix, docs | This report |

Integration defects caught that each agent's own checks missed: (1) `from conftest import …` collided once two test trees merged;
(2) CI's bare `pytest` could not import `app` (everyone had used `python -m pytest`) — fixed via `pythonpath` before the first CI run;
(3) security finding H-1 (fail-open JWT secret) fixed rather than deferred.

## Changes

**Backend**
- Fixed B1 (`Message.metadata` reserved → attribute `message_metadata`, column unchanged), B2 (interests relationship join),
  B3 (JWT `sub` must be a string; `type`/`iat`/`exp` enforced; access vs refresh not interchangeable), B4 (`/auth/refresh`).
- Contract-conformant auth, `/users/me` with onboarding status, profile CRUD with server-side 18+, `extra="forbid"` (no mass
  assignment), no coordinates in responses.
- Uniform error envelope for every non-2xx, including validation and unhandled errors (no internals leaked).
- Questionnaire: server-owned bank (`app/questionnaire/`), autosave, submit → server scoring; old client-score route removed.
  Scoring fixes: 0–100 range (was 20–100), strict validation, deterministic categorical outputs, attachment heuristic that can
  actually produce all four labels; `verify_*` free-text "authenticity" questions removed.
- Config fails closed: `ENVIRONMENT` defaults to `production`; weak/missing JWT secret refuses to start outside dev/testing.
  Gemini key optional and lazily configured (no AI calls in Sprint 1 flows). `DEBUG`/SQL echo off by default.
- WebSocket consent hot-fix: live sessions only on `ai_mediation` matches. Session cleanup task now actually runs.
- `create_all` removed from startup; Dockerfile runs `alembic upgrade head`.
- Dependencies: runtime vs dev split; unused `fastapi-cors`, `aioredis`, duplicate `httpx` removed; bcrypt pinned 4.0.1.

**Mobile (`mobile/`, new)** — Expo SDK 57, React Native 0.86, TypeScript, expo-router, zustand, expo-secure-store.
Routes: boot → `(auth)/login|register` → `(app)/profile-setup` → `(app)/questionnaire` → `(app)/home` (+ `profile-edit`);
guards route on server onboarding state so deep links can't skip steps. Central API client: 15 s timeout, typed endpoints,
`ApiError {status, code, message, fields}`, single-flight refresh-once-then-retry on 401, logout on rejected refresh
(transient refresh failures keep the session). Questionnaire: one question per screen, progress, resume, batched autosave with
retry/backoff, review + submit. Home: gentle personality snapshot (no clinical framing; attachment style omitted), clearly
labelled "coming soon" matching placeholder — no fake data.

**Repo** — `.github/workflows/ci.yml` (backend, mobile, e2e jobs); `.gitignore` gains a mobile block. The React/Vite `frontend/`
is untouched (kept as design/behaviour reference; it still does not build — see Known issues).

## Files (by area; 119 files, ~5.2k lines backend/docs, mobile mostly generated lockfile)
- Backend app: `app/{auth,config,database,errors,main,models,schemas}.py`, `app/routes/{auth,users,questionnaire,websocket}.py`,
  `app/services/{onboarding,questionnaire}.py`, `app/questionnaire/{__init__,bank,validation,scoring}.py`,
  `app/questionnaire_processor.py` (deprecated shim), minor lint fixes in `ai_service.py`/`ai_moderator.py`.
- Backend infra: `alembic.ini`, `alembic/`, `pyproject.toml`, `requirements*.txt`, `Dockerfile`, `.env.example`, `README.md`.
- Backend tests: `tests/*.py`, `tests/questionnaire/`, `tests/security/`.
- Mobile: `mobile/` (app routes under `src/app/`, logic under `src/{api,auth,features,theme,config.ts}`, tests in `__tests__/`
  and `src/__e2e__/`).
- Docs: `docs/API_CONTRACT.md`, `docs/QUESTIONNAIRE.md`, `docs/SECURITY_REVIEW_SPRINT1.md`, this report.

## Migrations
| Rev | Content | Backward compatibility |
|---|---|---|
| `0001` | Baseline = schema as of `1103f21` (verified identical via `pg_dump -s` diff) incl. 5 Postgres enum types | Existing `create_all` databases: `alembic stamp 0001` (documented in `backend/README.md`, not exercised — no such DB exists) |
| `0002` | `onboarding_answers` (unique user+question, cascade delete, indexed); `psychological_profiles.questionnaire_version`, `scored_at` | Additive only |

## API changes
New: `POST /auth/refresh` (functional), `GET /users/me`, `GET /questionnaire`, `GET /users/me/questionnaire`,
`PUT /users/me/questionnaire/answers`, `POST /users/me/questionnaire/submit`.
Changed: all errors use the envelope; register takes `{email, password}` only (extra fields ignored); profile create/update
validation + `409 PROFILE_EXISTS`; psych-profile response is nested (`big_five`, `values`, `love_languages`); JWT `sub` is a string.
Removed: `POST /users/me/psychological-profile` (client-supplied scores). Legacy `/matches/*`, `/users/interests`, WS unchanged
except the consent gate. Full spec: `docs/API_CONTRACT.md`.

## Test results
| Suite | Command | Result |
|---|---|---|
| Backend (Postgres 16) | `cd backend && pytest` | **831 passed, 1 xfailed** (~3 min) |
| Backend lint | `ruff check .` | clean |
| Migrations | upgrade → downgrade → upgrade → `alembic check` | clean, no drift |
| Mobile types | `npx tsc --noEmit` | clean |
| Mobile lint | `npx expo lint` | clean |
| Mobile unit | `npx jest` | **50 passed** |
| Mobile bundle | `npx expo export --platform ios --platform android` | both bundles exported |
| Vertical slice | `E2E_API_URL=… npm run test:e2e` (live uvicorn + Postgres) | **passed** (server access log confirms every call hit the API) |
| GitHub Actions CI | run #1 on `7d4d09b` | backend ✅ mobile ✅ e2e ✅ |

## Security findings (full detail: `docs/SECURITY_REVIEW_SPRINT1.md`)
- **Secrets:** none exposed in the tree or full history. Dev defaults only (compose DB password, dev JWT placeholder).
- **Fixed this sprint:** H-1 fail-open JWT secret; L-1/L-2 NUL bytes causing 500s; L-3 tokens without `exp` / non-ASCII-digit
  `sub`; login enumeration equalised (dummy bcrypt on unknown email); mass assignment blocked; scores server-only; WS consent gate.
- **Open, HIGH:** H-2 legacy `GET /matches/suggestions` side-effects + cross-user compatibility text; H-3 live sessions keyed by
  user; H-4 no rate limiting. (H-2/H-3 are the legacy matching/session code redesigned in Sprints 3–4.)
- **Open, MEDIUM:** M-1 dependency advisories (starlette, python-multipart, python-jose, …) — upgrade + `pip-audit` in CI;
  M-2 no request body size cap; M-3 JWT in WS query string; M-4 non-rotating 7-day refresh tokens (accepted for Sprint 1);
  M-5 no email verification.
- **Open, LOW:** bcrypt 72-byte truncation (strict xfail), homoglyph emails, `/docs` exposed in all environments, SQL params in
  error logs, no `iss`/`aud`, legacy route input bounds.

## Known issues
1. No device/simulator run (see top). Plain-http dev URLs may need platform config on physical devices.
2. `frontend/` (React web) still does not build (missing `src/lib/api.ts`); retained as reference per program direction.
3. Legacy matching/AI/WebSocket code is still live and still has the assessment's issues except the consent gate (Sprint 3–4).
4. Changing answers after submit leaves the stored profile until resubmission; `complete` stays true (no "stale" flag yet).
5. Refresh tokens are stateless (no rotation/revocation); logout is client-side only.
6. Postgres enum labels are stored uppercase (baseline behaviour); API uses lowercase values.
7. Full backend suite takes ~3 min (authz tests fully onboard a victim per test) — acceptable now, worth optimising.
8. The pinned Gemini SDK/model IDs are untested and likely obsolete; irrelevant until Sprint 2 introduces the provider abstraction.

## Manual testing
1. Postgres running; `cd backend && cp .env.example .env` (keep `ENVIRONMENT=development`), `pip install -r requirements.txt`,
   `alembic upgrade head`, `uvicorn app.main:app --reload`.
2. `cd mobile && npm ci && npx expo start`; iOS simulator uses `http://localhost:8000`, Android emulator `http://10.0.2.2:8000`,
   a physical device needs `EXPO_PUBLIC_API_URL=http://<LAN-IP>:8000` (see `mobile/README.md`).
3. Register → expect profile setup. Try a birth date < 18 years ago → inline error. Complete profile.
4. Answer ~10 questions, force-quit the app, reopen → still signed in, questionnaire resumes at the next unanswered question.
5. Toggle airplane mode mid-questionnaire → "Not saved yet — retrying…" indicator; reconnect → "All answers saved".
6. Finish and submit → home shows personality snapshot. Force-quit and reopen → home directly.
7. Sign out → login screen; sign in (any email casing) → home.

## Next sprint readiness
Ready for Sprint 2 (intelligent onboarding + compatibility profile). Foundations in place: server-owned question bank with
versioning, raw answers stored per question separate from computed scores, error envelope, Alembic, Postgres test harness,
mobile questionnaire UI driven entirely by the server definition, CI with a live E2E slice.
Recommended Sprint 2 prerequisites, in order: (1) rate limiting on `/auth/*` and every future AI route (H-4) — AI onboarding
makes this a cost issue; (2) dependency upgrades + `pip-audit` (M-1); (3) request body size cap (M-2).
Collected-but-unscored answers ready for Sprint 2 normalisation: `val_7`, `comm_3`, `rg_1`, `rg_2`, `pref_1`–`pref_5`.
