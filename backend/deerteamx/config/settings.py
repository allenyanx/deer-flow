"""DeerTeamX Configuration Settings

Loads environment variables from .env.deerteamx and provides typed configuration.
Follows the layered configuration strategy:
1. System environment variables (highest priority)
2. .env.deerteamx file
3. Default values in code

Configuration Categories:
- Infrastructure: Database, Redis, external services
- Security & Auth: JWT, encryption keys, rate limiting
- Integration: DeerFlow Gateway, internal communication
- Storage: File paths, temp directories
- Network: CORS, frontend URLs
- Observability: Metrics, tracing, logging
- Feature Flags: Toggle experimental features
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeerTeamXSettings(BaseSettings):
    """DeerTeamX application settings with comprehensive validation."""
    
    model_config = SettingsConfigDict(
        env_file=".env.deerteamx",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ========================================================================
    # Application Metadata
    # ========================================================================
    
    APP_NAME: str = Field(default="DeerTeamX", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    APP_ENV: str = Field(default="development", description="Environment: development/staging/production")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    
    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate application environment is one of allowed values."""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}, got '{v}'")
        return v
    
    # ========================================================================
    # Infrastructure
    # ========================================================================
    
    DATABASE_URL: str = Field(
        default="postgresql://deerteamx_user:password@localhost:5432/deerteamx_db",
        description="PostgreSQL connection string for DeerTeamX business logic"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Redis URL for distributed locks, rate limiting, and caching"
    )
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must start with 'postgresql://' or 'postgresql+asyncpg://'")
        return v
    
    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must start with 'redis://' or 'rediss://'")
        return v
    
    # ========================================================================
    # Internal Integration
    # ========================================================================
    
    DEERFLOW_GATEWAY_URL: str = Field(
        default="http://localhost:8001",
        description="DeerFlow Gateway endpoint for agent execution"
    )
    DEERFLOW_INTERNAL_SECRET: Optional[str] = Field(
        default=None,
        description="Internal communication secret for mutual authentication"
    )
    QDRANT_URL: str = Field(
        default="http://localhost:6334",
        description="Qdrant vector database URL for long-term memory"
    )
    
    # ========================================================================
    # Security & Auth
    # ========================================================================
    
    JWT_SECRET_KEY: str = Field(
        default="change-this-to-a-random-string-min-32-chars",
        min_length=32,
        description="JWT secret key for user sessions (min 32 chars)"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        ge=1,
        le=10080,
        description="Access token expiration in minutes (1 min - 7 days)"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Refresh token expiration in days (1-90 days)"
    )
    ENCRYPTION_MASTER_KEY: str = Field(
        default="aes-256-gcm-master-key-here-min-32-chars",
        min_length=32,
        description="AES-256-GCM master key for KMS encryption (min 32 chars)"
    )
    BCRYPT_ROUNDS: int = Field(
        default=12,
        ge=10,
        le=14,
        description="bcrypt hash rounds for password hashing (10-14)"
    )
    
    # Rate Limiting
    RATE_LIMIT_LOGIN_PER_MINUTE: int = Field(
        default=5,
        ge=1,
        description="Max login attempts per minute per IP"
    )
    RATE_LIMIT_REGISTER_PER_MINUTE: int = Field(
        default=3,
        ge=1,
        description="Max registration attempts per minute per IP"
    )
    RATE_LIMIT_EXECUTION_PER_MINUTE: int = Field(
        default=10,
        ge=1,
        description="Max execution triggers per minute per user"
    )
    RATE_LIMIT_IMPORT_PER_MINUTE: int = Field(
        default=3,
        ge=1,
        description="Max import tasks per minute per user"
    )
    RATE_LIMIT_READ_PER_MINUTE: int = Field(
        default=60,
        ge=1,
        description="Max read API calls per minute per user"
    )
    RATE_LIMIT_WRITE_PER_MINUTE: int = Field(
        default=30,
        ge=1,
        description="Max write API calls per minute per user"
    )
    
    # ========================================================================
    # Storage & Paths
    # ========================================================================
    
    IMPORT_TEMP_DIR: str = Field(
        default="/tmp/deerteamx_imports",
        description="Temporary directory for CrewAI import files"
    )
    EXPORT_RESULTS_DIR: str = Field(
        default="/mnt/user-data/exports",
        description="Directory for storing exported results"
    )
    KNOWLEDGE_BASE_DIR: str = Field(
        default="/mnt/user-data/knowledge",
        description="Persistent storage for knowledge source files"
    )
    LOG_DIR: str = Field(
        default="/var/log/deerteamx",
        description="Log file directory"
    )
    
    @field_validator("IMPORT_TEMP_DIR", "EXPORT_RESULTS_DIR", "KNOWLEDGE_BASE_DIR", "LOG_DIR")
    @classmethod
    def validate_directory_path(cls, v: str) -> str:
        """Validate directory path is absolute."""
        if not os.path.isabs(v):
            raise ValueError(f"Path must be absolute: {v}")
        return v
    
    # File Size Limits (in bytes)
    MAX_IMPORT_FILE_SIZE: int = Field(
        default=5 * 1024 * 1024,  # 5MB
        gt=0,
        description="Maximum CrewAI import file size in bytes"
    )
    MAX_KNOWLEDGE_FILE_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        gt=0,
        description="Maximum single knowledge file size in bytes"
    )
    MAX_TEAM_KNOWLEDGE_SIZE: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        gt=0,
        description="Maximum total knowledge size per team in bytes"
    )
    
    # ========================================================================
    # Frontend & Network
    # ========================================================================
    
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL for CORS and redirects"
    )
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,https://your-production-domain.com",
        description="Comma-separated list of allowed CORS origins"
    )
    WEBSOCKET_MAX_CONNECTIONS: int = Field(
        default=1000,
        gt=0,
        description="Maximum concurrent WebSocket connections"
    )
    WEBSOCKET_AUTH_TIMEOUT: int = Field(
        default=5,
        gt=0,
        description="WebSocket authentication timeout in seconds"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    # ========================================================================
    # Execution Engine
    # ========================================================================
    
    EXECUTION_LOCK_TTL: int = Field(
        default=1800,  # 30 minutes
        gt=0,
        description="Execution lock TTL in seconds"
    )
    EXECUTION_HEARTBEAT_INTERVAL: int = Field(
        default=300,  # 5 minutes
        gt=0,
        description="Lock heartbeat interval in seconds"
    )
    EXECUTION_TIMEOUT_DEFAULT: int = Field(
        default=1800,  # 30 minutes
        gt=0,
        description="Default execution timeout in seconds"
    )
    HUMAN_FEEDBACK_TIMEOUT_DEFAULT: int = Field(
        default=1800,  # 30 minutes
        ge=300,  # 5 minutes
        le=7200,  # 2 hours
        description="Default human feedback timeout in seconds (5min-2hr)"
    )
    
    # ========================================================================
    # Background Tasks
    # ========================================================================
    
    IMPORT_TASK_TIMEOUT: int = Field(
        default=60,
        gt=0,
        description="Import task timeout in seconds"
    )
    IMPORT_TASK_MAX_PARALLEL: int = Field(
        default=3,
        gt=0,
        description="Maximum parallel import tasks per user"
    )
    CLEANUP_IMPORT_TASKS_DAYS: int = Field(
        default=7,
        gt=0,
        description="Days to retain completed/failed import tasks"
    )
    CLEANUP_THREAD_DATA_DAYS: int = Field(
        default=30,
        gt=0,
        description="Days to retain completed execution thread data"
    )
    TEMP_FILE_TTL_IMPORT: int = Field(
        default=3600,  # 1 hour
        gt=0,
        description="TTL for import temp files in seconds"
    )
    TEMP_FILE_TTL_EXPORT: int = Field(
        default=86400,  # 24 hours
        gt=0,
        description="TTL for export temp files in seconds"
    )
    TEMP_FILE_TTL_KNOWLEDGE: int = Field(
        default=604800,  # 7 days
        gt=0,
        description="TTL for unlinked knowledge upload files in seconds"
    )
    
    # ========================================================================
    # LocalStorage TTL (Frontend Configuration)
    # ========================================================================
    
    LOCALSTORAGE_TTL_FORM_DRAFT: int = Field(
        default=7 * 24 * 3600,  # 7 days
        gt=0,
        description="TTL for form draft in localStorage (seconds)"
    )
    LOCALSTORAGE_TTL_DAG_CANVAS: int = Field(
        default=24 * 3600,  # 24 hours
        gt=0,
        description="TTL for DAG canvas state in localStorage (seconds)"
    )
    LOCALSTORAGE_TTL_IMPORT_PROGRESS: int = Field(
        default=70,  # 70 seconds (60s timeout + 10s buffer)
        gt=0,
        description="TTL for import progress in localStorage (seconds)"
    )
    SESSIONSTORAGE_TTL_SENSITIVE: int = Field(
        default=30 * 60,  # 30 minutes
        gt=0,
        description="TTL for sensitive fields in sessionStorage (seconds)"
    )
    
    # ========================================================================
    # Observability
    # ========================================================================
    
    ENABLE_METRICS: bool = Field(
        default=False,
        description="Enable Prometheus metrics exporter"
    )
    METRICS_PORT: int = Field(
        default=9090,
        gt=0,
        description="Prometheus metrics port"
    )
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = Field(
        default=None,
        description="OpenTelemetry OTLP endpoint for distributed tracing"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG/INFO/WARNING/ERROR/CRITICAL"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: json/text"
    )
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return v_upper
    
    # ========================================================================
    # Feature Flags
    # ========================================================================
    
    FEATURE_LONG_TERM_MEMORY: bool = Field(
        default=True,
        description="Enable long-term memory feature (requires Qdrant)"
    )
    FEATURE_CONSENSUS_MODE: bool = Field(
        default=True,
        description="Enable consensus process type"
    )
    FEATURE_HUMAN_FEEDBACK: bool = Field(
        default=True,
        description="Enable human feedback approval workflow"
    )
    FEATURE_STATE_PERSISTENCE: bool = Field(
        default=True,
        description="Enable state persistence for breakpoint resume"
    )
    FEATURE_CLI_EXECUTION: bool = Field(
        default=False,
        description="Enable CLI execution entry point (V1.1 planned)"
    )
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def validate_all(self) -> List[str]:
        """Run all custom validations and return list of warnings/errors.
        
        Returns:
            List of warning messages (empty list means all checks passed)
        """
        warnings = []
        
        # Check critical security keys in production
        if self.APP_ENV == "production":
            if self.JWT_SECRET_KEY == "change-this-to-a-random-string-min-32-chars":
                warnings.append("CRITICAL: JWT_SECRET_KEY is using default value in production!")
            if self.ENCRYPTION_MASTER_KEY == "aes-256-gcm-master-key-here-min-32-chars":
                warnings.append("CRITICAL: ENCRYPTION_MASTER_KEY is using default value in production!")
        
        # Check directory existence
        for dir_path in [self.IMPORT_TEMP_DIR, self.EXPORT_RESULTS_DIR, self.KNOWLEDGE_BASE_DIR]:
            if not Path(dir_path).exists():
                warnings.append(f"Directory does not exist: {dir_path}")
        
        # Check Qdrant availability if long-term memory enabled
        if self.FEATURE_LONG_TERM_MEMORY and not self.QDRANT_URL:
            warnings.append("FEATURE_LONG_TERM_MEMORY is enabled but QDRANT_URL is not set")
        
        return warnings


@lru_cache()
def get_settings() -> DeerTeamXSettings:
    """Get cached settings instance.
    
    Returns:
        DeerTeamXSettings instance with loaded configuration
    """
    return DeerTeamXSettings()
