"""Alembic: upgrade -> downgrade -> upgrade round trip and model/migration parity."""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.database import Base, engine
from app.models import User
from conftest import alembic_config

EXPECTED_TABLES = {
    "users", "user_profiles", "interests", "user_interests", "psychological_profiles",
    "onboarding_progress", "matches", "ai_sessions", "conversations", "messages",
    "ai_prompt_templates", "ai_conversation_logs",
}
PG_ENUMS = {"gender", "relationshipgoal", "matchstatus", "aisessionstatus", "messagetype"}


def _tables():
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def _pg_enums():
    with engine.connect() as conn:
        return {r[0] for r in conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))}


def test_models_match_migrations(db_schema):
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], diff


def test_upgrade_downgrade_upgrade_round_trip(db_schema):
    cfg = alembic_config()
    engine.dispose()  # no pooled connections holding locks
    try:
        assert _tables() == EXPECTED_TABLES

        command.downgrade(cfg, "base")
        engine.dispose()
        assert _tables() == set()
        if engine.dialect.name == "postgresql":
            assert _pg_enums() & PG_ENUMS == set(), "enum types not dropped on downgrade"

        command.upgrade(cfg, "head")
        engine.dispose()
        assert _tables() == EXPECTED_TABLES
        if engine.dialect.name == "postgresql":
            assert PG_ENUMS <= _pg_enums()
    finally:
        command.upgrade(cfg, "head")  # leave the session schema intact


def test_new_domain_columns_present(db_schema):
    insp = inspect(engine)
    users = {c["name"] for c in insp.get_columns("users")}
    assert {"first_name", "last_name"} <= users
    psych = {c["name"] for c in insp.get_columns("psychological_profiles")}
    assert "questionnaire_version" in psych
    onboarding = {c["name"]: c for c in insp.get_columns("onboarding_progress")}
    assert set(onboarding) == {
        "id", "user_id", "status", "current_section", "answers", "questionnaire_version",
        "created_at", "updated_at", "completed_at",
    }
    assert onboarding["user_id"]["nullable"] is False
    assert onboarding["status"]["nullable"] is False
    uniques = insp.get_unique_constraints("onboarding_progress")
    assert any(u["column_names"] == ["user_id"] for u in uniques)
    fks = insp.get_foreign_keys("onboarding_progress")
    assert fks[0]["referred_table"] == "users"
    assert (fks[0].get("options") or {}).get("ondelete") == "CASCADE"
    email_idx = [i for i in insp.get_indexes("users") if i["column_names"] == ["email"]]
    assert email_idx and email_idx[0]["unique"]


def test_user_delete_cascades(db, make_user):
    from app.models import OnboardingProgress, OnboardingStatus, PsychologicalProfile, UserProfile

    user = make_user()
    db.add_all([
        UserProfile(user_id=user.id, first_name="A"),
        PsychologicalProfile(user_id=user.id, openness=1),
        OnboardingProgress(user_id=user.id, status=OnboardingStatus.COMPLETED, answers={}),
    ])
    db.commit()
    # Delete with raw SQL to prove the DB-level ON DELETE CASCADE works.
    db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})
    db.commit()
    for model in (UserProfile, PsychologicalProfile, OnboardingProgress):
        assert db.query(model).count() == 0


def test_onboarding_defaults_and_status_check(db, make_user):
    import pytest
    from sqlalchemy.exc import IntegrityError, StatementError
    from app.models import OnboardingProgress, OnboardingStatus

    user = make_user()
    row = OnboardingProgress(user_id=user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    assert row.status is OnboardingStatus.NOT_STARTED
    assert row.answers == {}
    assert row.created_at is not None and row.updated_at is not None

    # Python side rejects invalid values...
    row.status = "bogus"
    with pytest.raises(StatementError):
        db.commit()
    db.rollback()
    # ...and the DB CHECK constraint rejects them too.
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE onboarding_progress SET status = 'bogus' WHERE id = :id"),
                   {"id": row.id})
    db.rollback()


def test_email_must_be_lowercase_at_db_level(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    db.add(User(email="Mixed@Example.com", hashed_password="x"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
