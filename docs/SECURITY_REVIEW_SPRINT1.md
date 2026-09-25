# Security Review: Sprint 1 (backend)

Scope: `backend/` at the integrated Sprint 1 branch (auth, profile, questionnaire, and the legacy routes still
exposed). Reviewed against `docs/API_CONTRACT.md` and `docs/REPOSITORY_ASSESSMENT.md` §14. `mobile/` and
`frontend/` were not reviewed.

How the findings were checked:
- **verified (test)**: a regression test in `backend/tests/security/` shows it.
- **verified (probe)**: reproduced against a running app (FastAPI TestClient + PostgreSQL), but no test was added.
- **code reading**: found by reading the code, not run.
- **not verified**: stated as a risk only.

## 1. Secret scan

Coverage: the working tree and the full history (`git log --all -p`, 17 commits, including the mobile merge),
plus the list of every file name ever committed. Patterns checked: Google `AIza…`, OpenAI `sk-…`/`sk-proj-…`,
Anthropic `sk-ant-…`, AWS `AKIA/ASIA…` and `aws_secret_access_key`, GitHub `gh[pousr]_…`/`github_pat_…`, GitLab,
Slack tokens and webhooks, Stripe `sk_/rk_/pk_(live|test)_…`, npm, SendGrid, PEM private keys, service-account JSON
(`private_key_id`, `"type": "service_account"`), literal JWTs, DB/Redis/AMQP URLs with credentials, and
`secret|password|api_key|token = <value>` assignments.

**No exposed secrets were found.** No real API keys, private keys, service-account files or literal JWTs appear
in any commit. The only files named like `.env` that were ever committed are `backend/.env.example` and
`frontend/.env.example`, and both hold placeholders only. `.gitignore` excludes `.env`, `.env.local` and `.env.*.local`.

Development defaults and placeholders that are not secrets, but must never reach a deployment:

| Value | Location | Note |
|---|---|---|
| DB password `datenow123` | `docker-compose.yml` (`POSTGRES_PASSWORD`, `DATABASE_URL`), `backend/.env.example` | Dev default. Rotate it if this compose file was ever used on a reachable host. |
| DB password `datenow` | test default `TEST_DATABASE_URL` (`backend/tests/conftest.py`, README) | Local test DB only. |
| `JWT_SECRET_KEY:-your-secret-key-change-in-production` | `docker-compose.yml:48` | A known placeholder. Only accepted because compose also sets `ENVIRONMENT=development`; see finding H-1. |
| `DEV_INSECURE_JWT_SECRET` | `backend/app/config.py` | Public by design and used only in development/testing; see H-1. |
| `test-only-jwt-secret-key-…` | `backend/tests/conftest.py` | Tests only. |
| `CHANGE_THIS_PASSWORD`, `your_…_here` placeholders | `DEPLOYMENT.md`, older docs | Placeholders. |

## 2. Findings

Severity reflects the Sprint 1 exposure: there is no production deployment yet, and these are pre-launch dating-app data.

| ID | Sev | Finding | Location | Evidence | Status |
|---|---|---|---|---|---|
| H-1 | HIGH | **Fail-open JWT secret.** `ENVIRONMENT` defaults to `development`, and in development a missing or weak `JWT_SECRET_KEY` is silently replaced by the public `DEV_INSECURE_JWT_SECRET`. A deployment that forgets `ENVIRONMENT` (or uses `docker-compose.yml` as-is, which hard-codes `ENVIRONMENT=development` plus a placeholder secret) signs tokens with a key that anyone can read in the repo, so anyone can forge a token for any user. | `app/config.py:36,72-88`, `docker-compose.yml:48-49` | `tests/security/test_sec_config.py::test_missing_environment_does_not_fall_back_to_public_secret` (strict xfail) | **open**. Proposed fix: default `ENVIRONMENT` to `production`, or require it to be set. This changes dev ergonomics and `tests/test_config.py::test_defaults`, so the owner should decide. |
| H-2 | HIGH | **Legacy `GET /matches/suggestions` has side effects and discloses data.** A GET creates `Match` rows (status `pending`) for other users without their action. It returns their user ids and a `compatibility_report` / `ai_recommendation` built from both users' private psychological profiles. `limit` has no upper bound, and every candidate costs one LLM call (cost/DoS amplification). | `app/routes/matches.py:26-116` | code reading (§14 of the assessment also covers the LLM fan-out) | open (legacy; redesign planned for Sprints 3–4) |
| H-3 | HIGH | Live WebSocket sessions are keyed by user, not by `(match_id, user)`. A user in two mediated matches can be attached to the wrong session, and a second socket replaces the first. This is carried over from assessment §14 and is still present. | `app/conversation_session.py:238-250`, `app/routes/websocket.py:80`, `app/websocket_manager.py` | code reading | open (legacy) |
| H-4 | HIGH | No rate limiting anywhere: login brute force, register spam, and AI endpoints. Carried over from §14. | all routes | code reading | open |
| M-1 | MEDIUM | **Dependencies with published advisories.** `pip-audit -r backend/requirements.txt` reports advisories for starlette 0.27.0 (about 7 distinct), python-multipart 0.0.6 (about 8), python-jose 3.3.0 (3, including CVE-2024-33663/33664, fixed in 3.4.0), fastapi 0.104.1, anyio 3.7.1, python-dotenv 1.0.0, protobuf 4.25.9 and ecdsa 0.19.2. Many target multipart forms or static/range file serving, which this app does not use, but that was **not verified per advisory**. | `backend/requirements.txt` | `pip-audit` run on 2026-09-25 | open. Upgrade FastAPI/Starlette and python-multipart; move off python-jose (to PyJWT or joserfc). |
| M-2 | MEDIUM | **No request body size limit.** Uvicorn and the app have no body cap, so a multi-MB JSON body is read and parsed before validation. `answers` is capped at 100 entries, but key and value lengths are not bounded. Unknown answer keys (up to 100, of any length) are echoed back in `error.fields`. | `app/main.py` (no limit), `app/routes/questionnaire.py:22-25`, `app/questionnaire/validation.py:95` | code reading; 101-entry cap tested in `test_answers_batch_limit` | open. Add a limit at the reverse proxy (for example `client_max_body_size 64k`) or a small ASGI middleware, and bound answer-key length. |
| M-3 | MEDIUM | **JWT in the WebSocket query string** (`/ws/conversation/{id}?token=…`), so it ends up in access and proxy logs. The token is a 30-minute access token. Carried over from §14. | `app/routes/websocket.py:37-44` | code reading | open. Use a short-lived single-use WS ticket. |
| M-4 | MEDIUM | Stateless tokens: no refresh-token rotation or reuse detection, no revocation, 7-day refresh lifetime. A stolen refresh token stays valid until it expires. Disabled users are rejected on refresh, which is correct. This matches the contract ("Sprint 1 tokens are stateless"). | `app/auth.py`, `app/routes/auth.py:67-71` | code reading | accepted for Sprint 1. Plan a server-side refresh-token family table. |
| M-5 | MEDIUM | No email verification, so anyone can register any address, including someone else's (account squatting). | `app/routes/auth.py` | code reading | open (planned trust & safety work) |
| L-1 | LOW | **NUL character in a password caused a 500** on register and login (`passlib.exc.PasswordValueError`). | `app/schemas.py` (`UserRegister`, `UserLogin`) | `test_sec_input_hardening.py::test_nul_byte_in_password_is_a_validation_error` | **fixed** (84502eb): 422 `VALIDATION_ERROR` |
| L-2 | LOW | **NUL character in profile text fields caused a 500**: PostgreSQL rejects NUL in text, and the driver raised `ValueError`. | `app/schemas.py` (`_ProfileFields`) | `test_sec_input_hardening.py::test_nul_byte_in_profile_{create,patch}_is_a_validation_error` | **fixed** (1d9a544): 422 |
| L-3 | LOW | **JWT claim validation gaps (defense in depth; exploiting them needs the signing key).** (a) Tokens without `exp` were accepted and never expire. (b) `sub` was checked with `str.isdigit()`: `"²"` raised in `int()` (500), and `"١"` (Arabic-Indic one) and `"１"` resolved to user 1. | `app/auth.py:decode_token` | `test_sec_jwt.py`, plus `no-exp` / `non-ascii-digit-sub` in the authn matrix | **fixed** (d584b2c): `exp` required, `sub` must fully match `[1-9][0-9]{0,17}` |
| L-4 | LOW | **bcrypt uses only the first 72 bytes.** Passwords may be up to 128 characters (up to 512 bytes in UTF-8), and bytes after 72 are ignored: `"x"*72 + "A"` logs in with `"x"*72 + "B"`. There is no DoS effect, because bcrypt cost does not depend on length. | `app/auth.py:26` | `test_sec_errors_enumeration.py::test_password_bytes_after_72_are_significant` (strict xfail) | open. Switch to `bcrypt_sha256` (passlib, with rehash-on-login), or argon2id, or cap passwords at 72 UTF-8 bytes (a contract change). |
| L-5 | LOW | Legacy `GET /matches/suggestions?limit=-5` returns a 500: PostgreSQL rejects the negative `LIMIT`. The body is the generic envelope, with no leak. | `app/routes/matches.py:28,71` | `test_sec_errors_enumeration.py::test_real_database_error_on_legacy_route_is_generic` | open (legacy). Use `limit: int = Query(10, ge=1, le=50)`. |
| L-6 | LOW | Server logs from the unhandled-error handler include SQLAlchemy's `[SQL: …] [parameters: …]`. For a failed `INSERT INTO users`, that would log the email and bcrypt hash. `print()` calls in the WS code log user ids and exception strings. | `app/errors.py:103`, `app/database.py` | verified (probe: log output shows the full statement and parameters) | open. Use `create_engine(..., hide_parameters=True)` and structured logging. |
| L-7 | LOW | Legacy `POST /users/me/interests` takes an unbounded list of ids and runs one query per id. | `app/routes/users.py:170-196` | verified (probe: 3,000 ids accepted) | open (legacy) |
| L-8 | LOW | Unicode look-alike emails create separate accounts. Addresses are NFC-normalised and lower-cased, but not NFKC-folded (for example fullwidth `ａ@example.com` vs `a@example.com`). Emails are never shown to other users, so the impact is limited to phishing or support confusion. Case, surrounding whitespace, domain case, zero-width characters and trailing dots are all handled correctly. | `app/schemas.py` (`UserRegister`), `app/auth.py:normalize_email` | verified (probe); correct variants tested in `test_email_variants_cannot_create_duplicate_accounts` | open (optional: reject non-ASCII local parts, or NFKC-fold before the uniqueness check) |
| L-9 | LOW | `/docs`, `/redoc` and `/openapi.json` are served in every environment. `/health` returns the environment name. | `app/main.py` | verified (probe) | open. Disable docs outside development. |
| L-10 | LOW | `/auth/register` answers `409 EMAIL_TAKEN` (account enumeration). This is required by the contract. | `app/routes/auth.py` | contract | accepted |
| L-11 | LOW | Tokens have no `iss` or `aud` claims. If the secret is ever shared with another service, tokens would be accepted across services. | `app/auth.py` | code reading | open |
| I-1 | INFO | Legacy `MatchResponse` exposes `user1_id` / `user2_id` (other users' internal ids). The contract's "never returned" rule covers `Profile`; legacy match routes are out of Sprint 1 scope. | `app/schemas.py:MatchResponse` | code reading | open (legacy) |

### Areas checked with no issue found (all backed by tests in `backend/tests/security/`)

- **JWT algorithm handling.** `alg: none` and `None`, an empty signature, HS512 signed with the server key,
  RS256 signed with a foreign RSA key, a wrong HMAC key, garbage and a 100 KB token are all rejected with
  `401 INVALID_TOKEN` on every 🔒 endpoint, on `/auth/refresh` and on the WebSocket (close 1008). `algorithms=[HS256]` is pinned.
- **Token type and subject.** A refresh token used as an access token (and the reverse), a missing or unknown
  `type`, and a non-numeric, negative, integer-typed or nonexistent-user `sub` all return `INVALID_TOKEN`.
  A missing header, `Basic`, or an empty `Bearer` returns `NOT_AUTHENTICATED`. Every 401 carries `WWW-Authenticate: Bearer`.
- **Endpoint coverage.** `test_endpoint_table_is_complete` walks the app's routes and fails if a route that
  depends on `get_current_user` is not in the table. `test_every_other_api_route_is_deliberately_public` pins
  the public set to register, login, refresh and `GET /users/interests`.
- **IDOR.** No route or parameter lets user A read or change user B's profile, answers or psychological profile:
  `?user_id=`, `?id=`, duplicated parameters, `X-User-Id` and similar headers, `{"user_id": B}` or `{"id": B}` in PATCH and PUT
  bodies, `/users/{id}/…` paths, scoped answer keys, and submit with a smuggled `user_id`. The victim's state is compared before and after.
- **Mass assignment.** `ProfileCreate`, `ProfileUpdate` and `AnswersUpdate` forbid extra fields. Server-owned fields
  (`id`, `user_id`, `is_profile_complete`, `latitude`, `longitude`, `photos`, `profile_photo_url`, `height_cm`,
  `distance_preference_km`, `created_at`, `updated_at`, `age`) are rejected with 422 on both POST and PATCH.
  Register ignores `id`, `is_active`, `is_verified`, `is_admin`, `hashed_password` and scores.
- **Psychological scores.** POST, PUT, PATCH and DELETE on `/users/me/psychological-profile` all return 405.
  Score or AI field names are rejected in answers and profile bodies. A submit body carrying scores is ignored,
  and scores are computed server-side. No request schema in the OpenAPI document declares a score field.
- **Response data.** No response schema contains `hashed_password`, `password`, `latitude`, `longitude`,
  `questionnaire_responses` or `ai_insights`. Live responses from every Sprint 1 route (plus `/users/me/interests`
  and `/matches/`) were checked with those columns filled in, and none of their values appear.
- **Error bodies.** OperationalError, DataError and IntegrityError (carrying SQL text, parameters and a DB
  name) injected into every Sprint 1 route, plus a real PostgreSQL error, all return exactly
  `{"error":{"code":"INTERNAL_ERROR","message":"Internal server error"}}` with no traceback or SQL.
  Malformed JSON returns a 4xx. Validation errors do not echo the password.
- **Login enumeration.** An unknown email and a wrong password give identical status, body and headers.
  Both paths run exactly one bcrypt verification at the same cost factor (a dummy hash is used for unknown
  emails), so timing is equal up to one indexed lookup. The disabled-account `403` is returned only after
  a correct password.
- **CORS.** The origin list is explicit (no `*`), and unknown origins get no `Access-Control-Allow-Origin`.
  `allow_credentials=True` is harmless with bearer tokens.
- **DEBUG.** It defaults to `False`, `app.debug` is `False`, and SQL echo is off.

## 3. Fixes made in this review

Each fix is a separate commit that includes its test. All of them are small input-validation changes:

1. `84502eb` fix(auth): reject NUL characters in passwords (422 instead of 500).
2. `1d9a544` fix(profile): reject NUL characters in profile text fields (422 instead of 500).
3. `d584b2c` fix(auth): require `exp` and a canonical numeric `sub` in JWTs.

## 4. Recommendations for Sprint 2+

1. **Before any deployment:** fix H-1 (fail closed on a missing `ENVIRONMENT` or secret; remove the compose placeholder secret), then add rate limiting (H-4) on `/auth/*` and every AI-backed route.
2. Upgrade FastAPI/Starlette and python-multipart, replace python-jose (M-1), and add `pip-audit` to CI.
3. Add a request body size cap (M-2) at the proxy and in the app. Bound answer-key length.
4. Move password hashing to argon2id or `bcrypt_sha256` with rehash-on-login (L-4).
5. Refresh-token rotation with reuse detection and a revocation list. Add `iss` and `aud` claims (M-4, L-11).
6. Replace the WS query-string JWT with a single-use ticket, and key live sessions by `(match_id, user_id)` (M-3, H-3).
7. When matching is redesigned (Sprints 3–4): make suggestion reads free of side effects, only show compatibility text that both users have consented to share, bound `limit`, and take the LLM off the request path (H-2, L-5).
8. Logging: `hide_parameters=True`, remove the `print()` calls, and redact PII from AI prompt logs (L-6, and §14).
9. Email verification and a block/report feature before real users (M-5, §14).
10. Keep `tests/security/test_sec_authn.py::PROTECTED_ENDPOINTS` current. The completeness test fails when a new protected route is added without an entry.
