"""Add execution_states table for breakpoint resume support

Revision ID: 003_add_execution_states
Revises: 002_add_team_locks
Create Date: 2026-04-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '003_add_execution_states'
down_revision = '002_add_team_locks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create execution_states table for breakpoint resume support.
    
    This migration is idempotent - safe to run multiple times.
    """
    from sqlalchemy import inspect
    
    # Check if table already exists
    inspector = inspect(op.get_bind())
    
    if 'execution_states' not in inspector.get_table_names():
        # Table doesn't exist, create it
        op.create_table(
            'execution_states',
            sa.Column('state_id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('execution_id', sa.String(length=64), nullable=False),
            sa.Column('task_id', sa.String(length=64), nullable=False),
            sa.Column('role_id', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),  # pending/running/completed/failed
            sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['execution_id'], ['executions.execution_id'], ondelete='CASCADE'),
        )
        
        # Create indexes for efficient queries
        op.create_index('idx_execution_states_execution_id', 'execution_states', ['execution_id'], unique=False)
        op.create_index('idx_execution_states_task_id', 'execution_states', ['task_id'], unique=False)
        op.create_index('idx_execution_states_status', 'execution_states', ['status'], unique=False)
        op.create_index('idx_execution_states_created_at', 'execution_states', ['created_at'], unique=False)
        
        print("✓ Created execution_states table with indexes")
    else:
        print("⚠ execution_states table already exists, skipping")


def downgrade() -> None:
    """Drop execution_states table."""
    
    op.drop_index('idx_execution_states_created_at', table_name='execution_states')
    op.drop_index('idx_execution_states_status', table_name='execution_states')
    op.drop_index('idx_execution_states_task_id', table_name='execution_states')
    op.drop_index('idx_execution_states_execution_id', table_name='execution_states')
    op.drop_table('execution_states')
