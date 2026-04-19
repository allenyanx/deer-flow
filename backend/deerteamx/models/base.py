"""DeerTeamX Database Models

This module defines all SQLAlchemy ORM models for DeerTeamX business logic.
All models are independent from DeerFlow's native database schema.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ============================================================================
# Mixin Classes
# ============================================================================

class TimestampMixin:
    """Adds created_at and updated_at timestamps to models."""
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft delete support via deleted_at timestamp."""
    
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)


# ============================================================================
# User Model
# ============================================================================

class User(Base, TimestampMixin):
    """User account model for authentication and authorization."""
    
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    role_type = Column(
        String(20),
        nullable=False,
        default="developer",
    )
    
    # Relationships
    teams = relationship("Team", back_populates="creator", foreign_keys="Team.creator_id")
    executions = relationship("Execution", back_populates="created_by_user", foreign_keys="Execution.created_by")
    templates = relationship("Template", back_populates="creator", foreign_keys="Template.creator_id")
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role_type}')>"


# ============================================================================
# Team Model
# ============================================================================

class Team(Base, TimestampMixin, SoftDeleteMixin):
    """Team configuration model - stores multi-agent collaboration workflows."""
    
    __tablename__ = "teams"
    
    team_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    execution_mode = Column(
        String(20),
        nullable=False,
    )  # 'static' or 'hybrid'
    status = Column(
        String(20),
        nullable=False,
        default="draft",
    )  # draft/executing/completed/failed
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    current_version = Column(String(20), nullable=False, default="v0.1.0")
    config_snapshot = Column(JSONB, nullable=False)  # Full team configuration snapshot
    
    # Relationships
    creator = relationship("User", back_populates="teams", foreign_keys=[creator_id])
    versions = relationship("TeamVersion", back_populates="team", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="team", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        # Partial unique index: enforce unique (name, creator_id) only for non-deleted teams
        Index(
            "uq_team_name_per_user",
            "name",
            "creator_id",
            unique=True,
            postgresql_where="deleted_at IS NULL"
        ),
        Index("idx_teams_creator_id", "creator_id"),
        Index("idx_teams_status", "status", postgresql_where="deleted_at IS NULL"),
    )
    
    def __repr__(self):
        return f"<Team(team_id='{self.team_id}', name='{self.name}', version='{self.current_version}')>"


# ============================================================================
# Execution Model
# ============================================================================

class Execution(Base, TimestampMixin):
    """Execution record model - tracks team workflow runs."""
    
    __tablename__ = "executions"
    
    execution_id = Column(String(64), primary_key=True)
    team_id = Column(String(64), ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False)
    thread_id = Column(String(64), unique=True, nullable=False)  # DeerFlow thread ID
    status = Column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending/running/completed/failed/cancelled/waiting_approval/approval_timeout/approval_rejected
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    execution_order = Column(JSONB, nullable=True)  # Array of role IDs in execution order
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_cost_cents = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    team = relationship("Team", back_populates="executions")
    created_by_user = relationship("User", back_populates="executions", foreign_keys=[created_by])
    
    # Constraints
    __table_args__ = (
        Index("idx_executions_team_id", "team_id"),
        Index("idx_executions_thread_id", "thread_id"),
        Index("idx_executions_created_at", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_executions_status", "status", postgresql_where="status = 'running'"),
    )
    
    def __repr__(self):
        return f"<Execution(execution_id='{self.execution_id}', status='{self.status}')>"


# ============================================================================
# Team Version Model
# ============================================================================

class TeamVersion(Base, TimestampMixin):
    """Team version history model - stores configuration snapshots."""
    
    __tablename__ = "team_versions"
    
    version_id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(64), ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    version_tag = Column(String(20), nullable=False)  # Semantic version vX.Y.Z
    config_snapshot = Column(JSONB, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    
    # Relationships
    team = relationship("Team", back_populates="versions")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("team_id", "version_number", name="uq_team_version_number"),
        Index("idx_team_versions_team_id", "team_id"),
    )
    
    def __repr__(self):
        return f"<TeamVersion(team_id='{self.team_id}', version='{self.version_tag}')>"


# ============================================================================
# Template Model
# ============================================================================

class Template(Base, TimestampMixin, SoftDeleteMixin):
    """Template model - reusable team configurations."""
    
    __tablename__ = "templates"
    
    template_id = Column(String(64), primary_key=True)
    template_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(
        String(20),
        nullable=False,
    )  # 'system' or 'personal'
    config_snapshot = Column(JSONB, nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)  # NULL for system templates
    usage_count = Column(Integer, default=0)
    
    # Relationships
    creator = relationship("User", back_populates="templates", foreign_keys=[creator_id])
    
    # Constraints
    __table_args__ = (
        Index("idx_templates_scope", "scope"),
        Index("idx_templates_creator_id", "creator_id", postgresql_where="scope = 'personal'"),
    )
    
    def __repr__(self):
        return f"<Template(template_id='{self.template_id}', name='{self.template_name}', scope='{self.scope}')>"
