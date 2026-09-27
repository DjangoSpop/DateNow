"""initial schema

Creates every table of the Sprint 1 domain model, including the new
onboarding_progress table, users.first_name/last_name and
psychological_profiles.questionnaire_version.

PostgreSQL: the native ENUM types (gender, relationshipgoal, matchstatus,
aisessionstatus, messagetype) are created implicitly by create_table and
dropped explicitly in downgrade(). onboarding_progress.status is a
VARCHAR(20) + CHECK constraint, not a native enum.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-27 09:30:37.878290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Native enum types created (on PostgreSQL) by the create_table calls below.
_PG_ENUM_TYPES = ("messagetype", "aisessionstatus", "relationshipgoal", "gender", "matchstatus")


def upgrade() -> None:
    op.create_table('ai_prompt_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('template', sa.Text(), nullable=False),
    sa.Column('variables', sa.JSON(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_prompt_templates')),
    sa.UniqueConstraint('name', name=op.f('uq_ai_prompt_templates_name'))
    )
    op.create_index(op.f('ix_ai_prompt_templates_id'), 'ai_prompt_templates', ['id'], unique=False)
    op.create_table('interests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_interests')),
    sa.UniqueConstraint('name', name=op.f('uq_interests_name'))
    )
    op.create_index(op.f('ix_interests_id'), 'interests', ['id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=50), nullable=True),
    sa.Column('last_name', sa.String(length=50), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('is_verified', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('email = lower(email)', name=op.f('ck_users_email_lowercase')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_table('ai_conversation_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.String(length=100), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('prompt', sa.Text(), nullable=True),
    sa.Column('response', sa.Text(), nullable=True),
    sa.Column('model_used', sa.String(length=50), nullable=True),
    sa.Column('tokens_used', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_ai_conversation_logs_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_conversation_logs'))
    )
    op.create_index(op.f('ix_ai_conversation_logs_id'), 'ai_conversation_logs', ['id'], unique=False)
    op.create_table('matches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user1_id', sa.Integer(), nullable=False),
    sa.Column('user2_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'accepted', 'rejected', 'ai_mediation', 'direct_chat', 'ended', name='matchstatus'), nullable=True),
    sa.Column('overall_compatibility', sa.Float(), nullable=True),
    sa.Column('personality_compatibility', sa.Float(), nullable=True),
    sa.Column('values_compatibility', sa.Float(), nullable=True),
    sa.Column('interests_compatibility', sa.Float(), nullable=True),
    sa.Column('lifestyle_compatibility', sa.Float(), nullable=True),
    sa.Column('compatibility_report', sa.Text(), nullable=True),
    sa.Column('ai_recommendation', sa.Text(), nullable=True),
    sa.Column('matched_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('ai_mediation_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('direct_chat_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('user1_interested', sa.Boolean(), nullable=True),
    sa.Column('user2_interested', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user1_id'], ['users.id'], name=op.f('fk_matches_user1_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user2_id'], ['users.id'], name=op.f('fk_matches_user2_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_matches'))
    )
    op.create_index(op.f('ix_matches_id'), 'matches', ['id'], unique=False)
    op.create_index(op.f('ix_matches_user1_id'), 'matches', ['user1_id'], unique=False)
    op.create_index(op.f('ix_matches_user2_id'), 'matches', ['user2_id'], unique=False)
    op.create_table('onboarding_progress',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='not_started', nullable=False),
    sa.Column('current_section', sa.String(length=50), nullable=True),
    sa.Column('answers', sa.JSON(), nullable=False),
    sa.Column('questionnaire_version', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('not_started', 'in_progress', 'completed')", name=op.f('ck_onboarding_progress_status_valid')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_onboarding_progress_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_onboarding_progress')),
    sa.UniqueConstraint('user_id', name=op.f('uq_onboarding_progress_user_id'))
    )
    op.create_index(op.f('ix_onboarding_progress_id'), 'onboarding_progress', ['id'], unique=False)
    op.create_table('psychological_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('openness', sa.Float(), nullable=True),
    sa.Column('conscientiousness', sa.Float(), nullable=True),
    sa.Column('extraversion', sa.Float(), nullable=True),
    sa.Column('agreeableness', sa.Float(), nullable=True),
    sa.Column('neuroticism', sa.Float(), nullable=True),
    sa.Column('family_orientation', sa.Float(), nullable=True),
    sa.Column('career_ambition', sa.Float(), nullable=True),
    sa.Column('adventure_seeking', sa.Float(), nullable=True),
    sa.Column('social_consciousness', sa.Float(), nullable=True),
    sa.Column('spiritual_religious', sa.Float(), nullable=True),
    sa.Column('communication_style', sa.String(length=50), nullable=True),
    sa.Column('conflict_resolution', sa.String(length=50), nullable=True),
    sa.Column('love_language_words', sa.Float(), nullable=True),
    sa.Column('love_language_acts', sa.Float(), nullable=True),
    sa.Column('love_language_gifts', sa.Float(), nullable=True),
    sa.Column('love_language_time', sa.Float(), nullable=True),
    sa.Column('love_language_touch', sa.Float(), nullable=True),
    sa.Column('attachment_style', sa.String(length=50), nullable=True),
    sa.Column('questionnaire_responses', sa.JSON(), nullable=True),
    sa.Column('ai_insights', sa.Text(), nullable=True),
    sa.Column('questionnaire_version', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_psychological_profiles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_psychological_profiles')),
    sa.UniqueConstraint('user_id', name=op.f('uq_psychological_profiles_user_id'))
    )
    op.create_index(op.f('ix_psychological_profiles_id'), 'psychological_profiles', ['id'], unique=False)
    op.create_table('user_interests',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('interest_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['interest_id'], ['interests.id'], name=op.f('fk_user_interests_interest_id_interests'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_interests_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'interest_id', name=op.f('pk_user_interests'))
    )
    op.create_table('user_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('first_name', sa.String(length=50), nullable=False),
    sa.Column('last_name', sa.String(length=50), nullable=True),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('gender', sa.Enum('male', 'female', 'non_binary', 'other', name='gender'), nullable=True),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('height_cm', sa.Integer(), nullable=True),
    sa.Column('looking_for_gender', sa.JSON(), nullable=True),
    sa.Column('age_preference_min', sa.Integer(), nullable=True),
    sa.Column('age_preference_max', sa.Integer(), nullable=True),
    sa.Column('distance_preference_km', sa.Integer(), nullable=True),
    sa.Column('relationship_goal', sa.Enum('serious', 'casual', 'friendship', 'unsure', name='relationshipgoal'), nullable=True),
    sa.Column('photos', sa.JSON(), nullable=True),
    sa.Column('profile_photo_url', sa.String(), nullable=True),
    sa.Column('is_profile_complete', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_profiles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_profiles')),
    sa.UniqueConstraint('user_id', name=op.f('uq_user_profiles_user_id'))
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)
    op.create_table('ai_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('active', 'completed', 'paused', 'cancelled', name='aisessionstatus'), nullable=True),
    sa.Column('questions_asked', sa.Integer(), nullable=True),
    sa.Column('responses_collected', sa.Integer(), nullable=True),
    sa.Column('session_data', sa.JSON(), nullable=True),
    sa.Column('user_insights', sa.Text(), nullable=True),
    sa.Column('compatibility_notes', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], name=op.f('fk_ai_sessions_match_id_matches'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_ai_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_sessions'))
    )
    op.create_index(op.f('ix_ai_sessions_id'), 'ai_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_ai_sessions_match_id'), 'ai_sessions', ['match_id'], unique=False)
    op.create_index(op.f('ix_ai_sessions_user_id'), 'ai_sessions', ['user_id'], unique=False)
    op.create_table('conversations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('is_ai_mediated', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], name=op.f('fk_conversations_match_id_matches'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_conversations')),
    sa.UniqueConstraint('match_id', name=op.f('uq_conversations_match_id'))
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('ai_session_id', sa.Integer(), nullable=True),
    sa.Column('sender_id', sa.Integer(), nullable=True),
    sa.Column('message_type', sa.Enum('ai_question', 'user_response', 'ai_insight', 'system', 'direct_message', name='messagetype'), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('metadata', sa.JSON(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.ForeignKeyConstraint(['ai_session_id'], ['ai_sessions.id'], name=op.f('fk_messages_ai_session_id_ai_sessions'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_messages_conversation_id_conversations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], name=op.f('fk_messages_sender_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_messages'))
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_conversations_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_ai_sessions_user_id'), table_name='ai_sessions')
    op.drop_index(op.f('ix_ai_sessions_match_id'), table_name='ai_sessions')
    op.drop_index(op.f('ix_ai_sessions_id'), table_name='ai_sessions')
    op.drop_table('ai_sessions')
    op.drop_index(op.f('ix_user_profiles_id'), table_name='user_profiles')
    op.drop_table('user_profiles')
    op.drop_table('user_interests')
    op.drop_index(op.f('ix_psychological_profiles_id'), table_name='psychological_profiles')
    op.drop_table('psychological_profiles')
    op.drop_index(op.f('ix_onboarding_progress_id'), table_name='onboarding_progress')
    op.drop_table('onboarding_progress')
    op.drop_index(op.f('ix_matches_user2_id'), table_name='matches')
    op.drop_index(op.f('ix_matches_user1_id'), table_name='matches')
    op.drop_index(op.f('ix_matches_id'), table_name='matches')
    op.drop_table('matches')
    op.drop_index(op.f('ix_ai_conversation_logs_id'), table_name='ai_conversation_logs')
    op.drop_table('ai_conversation_logs')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_interests_id'), table_name='interests')
    op.drop_table('interests')
    op.drop_index(op.f('ix_ai_prompt_templates_id'), table_name='ai_prompt_templates')
    op.drop_table('ai_prompt_templates')

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_name in _PG_ENUM_TYPES:
            sa.Enum(name=enum_name).drop(bind, checkfirst=True)
