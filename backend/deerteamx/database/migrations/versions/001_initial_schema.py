"""Initial DeerTeamX schema - Create all tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-04-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all DeerTeamX tables."""
    
    # ========================================================================
    # Users table
    # ========================================================================
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('role_type', sa.String(length=20), nullable=False, server_default='developer'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('idx_users_username', 'users', ['username'], unique=False)
    
    # ========================================================================
    # Teams table
    # ========================================================================
    op.create_table(
        'teams',
        sa.Column('team_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('execution_mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_version', sa.String(length=20), nullable=False, server_default='v0.1.0'),
        sa.Column('config_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('team_id'),
        sa.UniqueConstraint('name', 'creator_id', name='uq_team_name_per_user', postgresql_where=sa.text('deleted_at IS NULL')),
    )
    op.create_index('idx_teams_creator_id', 'teams', ['creator_id'], unique=False)
    op.create_index('idx_teams_status', 'teams', ['status'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    
    # ========================================================================
    # Executions table
    # ========================================================================
    op.create_table(
        'executions',
        sa.Column('execution_id', sa.String(length=64), nullable=False),
        sa.Column('team_id', sa.String(length=64), nullable=False),
        sa.Column('thread_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_order', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_input_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_output_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_cost_cents', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('execution_id'),
        sa.UniqueConstraint('thread_id'),
    )
    op.create_index('idx_executions_team_id', 'executions', ['team_id'], unique=False)
    op.create_index('idx_executions_thread_id', 'executions', ['thread_id'], unique=False)
    op.create_index('idx_executions_created_at', 'executions', ['created_at'], unique=False, postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_executions_status', 'executions', ['status'], unique=False, postgresql_where=sa.text("status = 'running'"))
    
    # ========================================================================
    # Team versions table
    # ========================================================================
    op.create_table(
        'team_versions',
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.String(length=64), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('version_tag', sa.String(length=20), nullable=False),
        sa.Column('config_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('version_id'),
        sa.UniqueConstraint('team_id', 'version_number', name='uq_team_version_number'),
    )
    op.create_index('idx_team_versions_team_id', 'team_versions', ['team_id'], unique=False)
    
    # ========================================================================
    # Templates table
    # ========================================================================
    op.create_table(
        'templates',
        sa.Column('template_id', sa.String(length=64), nullable=False),
        sa.Column('template_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column('config_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('template_id'),
    )
    op.create_index('idx_templates_scope', 'templates', ['scope'], unique=False)
    op.create_index('idx_templates_creator_id', 'templates', ['creator_id'], unique=False, postgresql_where=sa.text("scope = 'personal'"))


def downgrade() -> None:
    """Drop all DeerTeamX tables in reverse order."""
    op.drop_index('idx_templates_creator_id', table_name='templates')
    op.drop_index('idx_templates_scope', table_name='templates')
    op.drop_table('templates')
    
    op.drop_index('idx_team_versions_team_id', table_name='team_versions')
    op.drop_table('team_versions')
    
    op.drop_index('idx_executions_status', table_name='executions')
    op.drop_index('idx_executions_created_at', table_name='executions')
    op.drop_index('idx_executions_thread_id', table_name='executions')
    op.drop_index('idx_executions_team_id', table_name='executions')
    op.drop_table('executions')
    
    op.drop_index('idx_teams_status', table_name='teams')
    op.drop_index('idx_teams_creator_id', table_name='teams')
    op.drop_table('teams')
    
    op.drop_index('idx_users_username', table_name='users')
    op.drop_table('users')
