"""DeerTeamX Configuration Settings

Loads environment variables from .env.deerteamx and provides typed configuration.
Follows the layered configuration strategy:
1. System environment variables (highest priority)
2. .env.deerteamx file
3. Default values in code
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeerTeamXSettings(BaseSettings):
    """DeerTeamX application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env.deerteamx",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ========================================================================
    # Infrastructure
    # ========================================================================
    
    DATABASE_URL: str = "postgresql://deerteamx_user:password@localhost:5432/deerteamx_db"
    REDIS_URL: str = "redis://localhost:6379/1"
    
    # ========================================================================
    # Internal Integration
    # ========================================================================
    
    DEERFLOW_GATEWAY_URL: str = "http://localhost:8001"
    DEERFLOW_INTERNAL_SECRET: Optional[str] = None
    
    # ========================================================================
    # Security & Auth
    # ========================================================================
    
    JWT_SECRET_KEY: str = "change-this-to-a-random-string-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_MASTER_KEY: str = "aes-256-gcm-master-key-here-min-32-chars"
    
    # ========================================================================
    # Storage & Paths
    # ========================================================================
    
    IMPORT_TEMP_DIR: str = "/tmp/deerteamx_imports"
    EXPORT_RESULTS_DIR: str = "/mnt/user-data/exports"
    
    # ========================================================================
    # Frontend & Network
    # ========================================================================
    
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000,https://your-production-domain.com"
    
    # ========================================================================
    # Observability (Optional)
    # ========================================================================
    
    ENABLE_METRICS: bool = False
    METRICS_PORT: int = 9090
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None


@lru_cache()
def get_settings() -> DeerTeamXSettings:
    """Get cached settings instance.
    
    Returns:
        DeerTeamXSettings instance with loaded configuration
    """
    return DeerTeamXSettings()
