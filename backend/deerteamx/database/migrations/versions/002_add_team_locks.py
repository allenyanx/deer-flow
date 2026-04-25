"""Add team_locks table for distributed locking

Revision ID: 002_add_team_locks
Revises: 001_initial_schema
Create Date: 2026-04-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_team_locks'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create team_locks table for distributed lock management.
    
    This migration is idempotent - safe to run multiple times.
    """
    from sqlalchemy import inspect
    
    # Check if table already exists
    inspector = inspect(op.get_bind())
    
    if 'team_locks' not in inspector.get_table_names():
        # Table doesn't exist, create it
        op.create_table(
            'team_locks',
            sa.Column('team_id', sa.String(length=64), nullable=False),
            sa.Column('owner_id', sa.String(length=64), nullable=False),
            sa.Column('acquired_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('lock_token', sa.String(length=64), nullable=False),
            sa.PrimaryKeyConstraint('team_id'),
        )
        op.create_index('idx_team_locks_expires_at', 'team_locks', ['expires_at'], unique=False)
        print("✓ Created team_locks table with index")
    else:
        # Table already exists, check if index exists
        indexes = inspector.get_indexes('team_locks')
        index_names = [idx['name'] for idx in indexes]
        
        if 'idx_team_locks_expires_at' not in index_names:
            # Index doesn't exist, create it
            op.create_index('idx_team_locks_expires_at', 'team_locks', ['expires_at'], unique=False)
            print("✓ Created missing index idx_team_locks_expires_at")
        else:
            print("⚠ team_locks table and index already exist, skipping")


def downgrade() -> None:
    """Drop team_locks table."""
    
    op.drop_index('idx_team_locks_expires_at', table_name='team_locks')
    op.drop_table('team_locks')
