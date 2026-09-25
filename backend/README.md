# DateNow backend

FastAPI + SQLAlchemy 2.0 (sync) + PostgreSQL. API contract: `docs/API_CONTRACT.md`.

## Setup

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt        # runtime deps: requirements.txt
cp .env.example .env                       # set DATABASE_URL (and JWT_SECRET_KEY outside development)
alembic upgrade head                       # the app never creates tables itself
uvicorn app.main:app --reload
```

## Configuration notes

- `JWT_SECRET_KEY`: startup is refused if it is missing, a known placeholder, or shorter than 32 characters,
  unless `ENVIRONMENT` is `development` or `testing` (then an insecure dev key is used, with a warning).
- `GEMINI_API_KEY` is optional. AI features raise only when actually used.
- `DEBUG` defaults to `False` (it enables SQL echo).

## Migrations (Alembic)

- `alembic/versions/0001_baseline_schema.py`: the pre-Sprint-1 schema (as `create_all` produced it at 1103f21).
- `alembic/versions/0002_sprint1_onboarding_answers.py`: `onboarding_answers` table and the
  `psychological_profiles.questionnaire_version` / `scored_at` columns.
- The URL comes from `DATABASE_URL` (via `app.config.settings`), not `alembic.ini`.
- After changing models: `alembic revision --autogenerate -m "..."`, review the result, then run `alembic check`.
- An existing database that was created by the old `create_all` startup has the 0001 schema: run
  `alembic stamp 0001 && alembic upgrade head`.

## Tests

The tests need PostgreSQL. By default they use `postgresql://datenow:datenow@localhost:5432/datenow_test`
(override with `TEST_DATABASE_URL`). The schema is migrated once per session and truncated between tests.

```bash
pytest            # from backend/
ruff check .
```
