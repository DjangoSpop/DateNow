# Backend: migrations and tests

## Schema / migrations

The schema is managed only by Alembic; the app never calls `create_all`.

```bash
cd backend
export DATABASE_URL=postgresql://datenow:...@localhost:5432/datenow
export JWT_SECRET_KEY=...            # required
alembic upgrade head                 # apply
alembic downgrade base               # drop everything (incl. PG enum types)
alembic revision --autogenerate -m "describe change"   # then hand-review!
alembic check                        # fails if models and migrations differ
```

## Running tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest                                   # SQLite (temp file), no services needed
TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/datenow_test pytest   # PostgreSQL
```

- `tests/conftest.py` sets the test env vars (JWT secret, `ENVIRONMENT=testing`,
  no Gemini key, rate limiting off) **before** importing the app.
- The schema is built once per session with `alembic downgrade base` +
  `alembic upgrade head` on `TEST_DATABASE_URL`. Every DB test starts with empty
  tables (truncate before/after). The PostgreSQL test DB is wiped, so don't
  point it at real data.
- Fixtures: `client`, `db`, `make_user`, `auth_headers`, `make_token` (forged,
  expired or wrong-type JWTs), `profile_payload`.
- Layout: `tests/api/` (endpoint behaviour), `tests/security/` (tokens, rate
  limiting, config hardening), `tests/db/` (migrations, constraints).

## Auth rate limiting

`AUTH_RATE_LIMIT_PER_MINUTE` (default 10, `0` disables) caps
`POST /auth/login` and `POST /auth/register` per client IP, and login also per
email. The limiter is in-process: each worker keeps its own counters, so a
Redis-backed limiter is needed before scaling out. The client IP is the direct
peer address; `X-Forwarded-For` is not trusted.
