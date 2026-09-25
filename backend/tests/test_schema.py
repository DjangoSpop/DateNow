"""Model import regressions (B1/B2) and model <-> migration drift."""
import os
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers

from app.database import Base, engine
from app.models import (
    Interest, Message, MessageType, OnboardingAnswer, PsychologicalProfile, User, UserProfile, user_interests,
)

def alembic_config() -> Config:
    """Same config the root conftest migrates with (it sets DATABASE_URL before collection).

    Built here rather than imported from conftest: several conftest.py files exist, and
    `import conftest` resolves to whichever pytest loaded first.
    """
    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.attributes["url"] = os.environ["DATABASE_URL"]
    cfg.attributes["configure_logger"] = False
    return cfg


def test_models_import_and_mappers_configure():
    configure_mappers()
    assert Message.__mapper__.attrs["message_metadata"].columns[0].name == "metadata"
    assert isinstance(Base.metadata, MetaData)  # not shadowed by a column


def test_message_metadata_roundtrip(db):
    db.add(Message(content="hi", message_type=MessageType.SYSTEM, message_metadata={"k": "v"}))
    db.commit()
    row = db.execute(text("SELECT metadata FROM messages")).scalar_one()
    assert row == {"k": "v"}


def test_user_profile_interests_relationship(db):
    user = User(email="x@example.com", hashed_password="x")
    db.add(user)
    db.flush()
    profile = UserProfile(user_id=user.id, first_name="X")
    music, art = Interest(name="music"), Interest(name="art")
    db.add_all([profile, music, art])
    db.flush()
    db.execute(user_interests.insert().values(user_id=user.id, interest_id=music.id))
    db.commit()
    db.expire_all()
    assert [i.name for i in db.get(UserProfile, profile.id).interests] == ["music"]
    assert [p.first_name for p in db.get(Interest, music.id).users] == ["X"]
    # writes through the relationship store users.id in user_interests.user_id
    profile.interests.append(art)
    db.commit()
    rows = db.execute(text("SELECT user_id, interest_id FROM user_interests ORDER BY interest_id")).all()
    assert rows == [(user.id, music.id), (user.id, art.id)]


def test_onboarding_answer_constraints(db):
    db.add(User(email="y@example.com", hashed_password="x"))
    db.commit()
    db.add(OnboardingAnswer(user_id=1, question_id="bf_1", value=3, questionnaire_version="ipip-v1"))
    db.commit()
    db.add(OnboardingAnswer(user_id=1, question_id="bf_1", value=4, questionnaire_version="ipip-v1"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    # ON DELETE CASCADE at the database level
    db.execute(text("DELETE FROM users WHERE id = 1"))
    db.commit()
    assert db.query(OnboardingAnswer).count() == 0


def test_psych_profile_new_columns():
    cols = {c["name"] for c in inspect(engine).get_columns("psychological_profiles")}
    assert {"questionnaire_version", "scored_at"} <= cols
    assert {"questionnaire_version", "scored_at"} <= set(PsychologicalProfile.__table__.c.keys())


def test_alembic_head_matches_models():
    script = ScriptDirectory.from_config(alembic_config())
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        assert ctx.get_current_revision() == script.get_current_head()
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], diff


def test_single_head():
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1
