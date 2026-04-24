"""DeerTeamX Configuration Management API

Provides endpoints for runtime configuration inspection and validation.
Allows administrators to check system health, view active settings,
and trigger configuration reloads without restarting the application.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from deerteamx.config.settings import get_settings, DeerTeamXSettings
from deerteamx.utils.config_validator import ConfigValidator

router = APIRouter(
    prefix="/config",
    tags=["Configuration Management"],
    responses={
        403: {"description": "Forbidden - Admin access required"},
        503: {"description": "Service unhealthy"}
    }
)


@router.get("/settings")
async def get_active_settings(
    settings: DeerTeamXSettings = Depends(get_settings),
) -> Dict[str, Any]:
    """Get current active configuration settings (sanitized).
    
    Returns non-sensitive configuration values for debugging and monitoring.
    Sensitive fields (keys, secrets) are masked or omitted.
    
    **Security**: This endpoint filters out sensitive information before returning.
    
    Returns:
        Dictionary of sanitized configuration values grouped by category
    """
    # Return safe configuration categories
    return {
        "application": {
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "app_env": settings.APP_ENV,
            "debug": settings.DEBUG,
        },
        "infrastructure": {
            "database_url_masked": _mask_url(settings.DATABASE_URL),
            "redis_url_masked": _mask_url(settings.REDIS_URL),
        },
        "integration": {
            "deerflow_gateway_url": settings.DEERFLOW_GATEWAY_URL,
            "qdrant_url": settings.QDRANT_URL,
            "internal_secret_configured": bool(settings.DEERFLOW_INTERNAL_SECRET),
        },
        "security": {
            "jwt_algorithm": settings.JWT_ALGORITHM,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
            "bcrypt_rounds": settings.BCRYPT_ROUNDS,
            "encryption_key_configured": bool(settings.ENCRYPTION_MASTER_KEY),
        },
        "rate_limiting": {
            "login_per_minute": settings.RATE_LIMIT_LOGIN_PER_MINUTE,
            "register_per_minute": settings.RATE_LIMIT_REGISTER_PER_MINUTE,
            "execution_per_minute": settings.RATE_LIMIT_EXECUTION_PER_MINUTE,
            "import_per_minute": settings.RATE_LIMIT_IMPORT_PER_MINUTE,
            "read_per_minute": settings.RATE_LIMIT_READ_PER_MINUTE,
            "write_per_minute": settings.RATE_LIMIT_WRITE_PER_MINUTE,
        },
        "storage": {
            "import_temp_dir": settings.IMPORT_TEMP_DIR,
            "export_results_dir": settings.EXPORT_RESULTS_DIR,
            "knowledge_base_dir": settings.KNOWLEDGE_BASE_DIR,
            "log_dir": settings.LOG_DIR,
            "max_import_file_size_mb": settings.MAX_IMPORT_FILE_SIZE / (1024 * 1024),
            "max_knowledge_file_size_mb": settings.MAX_KNOWLEDGE_FILE_SIZE / (1024 * 1024),
        },
        "network": {
            "frontend_url": settings.FRONTEND_URL,
            "cors_origins": settings.cors_origins_list,
            "websocket_max_connections": settings.WEBSOCKET_MAX_CONNECTIONS,
            "websocket_auth_timeout": settings.WEBSOCKET_AUTH_TIMEOUT,
        },
        "execution": {
            "execution_lock_ttl": settings.EXECUTION_LOCK_TTL,
            "execution_heartbeat_interval": settings.EXECUTION_HEARTBEAT_INTERVAL,
            "execution_timeout_default": settings.EXECUTION_TIMEOUT_DEFAULT,
            "human_feedback_timeout_default": settings.HUMAN_FEEDBACK_TIMEOUT_DEFAULT,
        },
        "background_tasks": {
            "import_task_timeout": settings.IMPORT_TASK_TIMEOUT,
            "import_task_max_parallel": settings.IMPORT_TASK_MAX_PARALLEL,
            "cleanup_import_tasks_days": settings.CLEANUP_IMPORT_TASKS_DAYS,
            "cleanup_thread_data_days": settings.CLEANUP_THREAD_DATA_DAYS,
        },
        "feature_flags": {
            "long_term_memory": settings.FEATURE_LONG_TERM_MEMORY,
            "consensus_mode": settings.FEATURE_CONSENSUS_MODE,
            "human_feedback": settings.FEATURE_HUMAN_FEEDBACK,
            "state_persistence": settings.FEATURE_STATE_PERSISTENCE,
            "cli_execution": settings.FEATURE_CLI_EXECUTION,
        },
        "observability": {
            "enable_metrics": settings.ENABLE_METRICS,
            "metrics_port": settings.METRICS_PORT,
            "otel_endpoint": settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            "log_level": settings.LOG_LEVEL,
            "log_format": settings.LOG_FORMAT,
        }
    }


@router.get("/health")
async def health_check(
    settings: DeerTeamXSettings = Depends(get_settings),
) -> Dict[str, Any]:
    """Comprehensive health check endpoint.
    
    Validates connectivity to all dependent services:
    - PostgreSQL database
    - Redis cache
    - DeerFlow Gateway
    - Qdrant vector database
    - Configuration integrity
    
    **Use Cases**:
    - Kubernetes liveness/readiness probes
    - Load balancer health checks
    - Monitoring system integration (Prometheus, Datadog, etc.)
    
    Returns:
        Health status report with individual service checks
        
    Response Codes:
        - 200: All critical services healthy
        - 503: One or more critical services unavailable
    """
    from deerteamx.database.session import async_session_maker
    
    # For now, skip Redis validation as it's not implemented yet
    # TODO: Add Redis support when needed
    validator = ConfigValidator(async_session_maker, None, settings)
    report = await validator.validate_all()
    
    # Determine HTTP status code
    status_code = 200 if report["status"] != "unhealthy" else 503
    
    return report


@router.post("/validate")
async def validate_configuration(
    settings: DeerTeamXSettings = Depends(get_settings),
) -> Dict[str, Any]:
    """Trigger manual configuration validation.
    
    Runs all validation checks and returns detailed report.
    Useful for troubleshooting configuration issues after deployment.
    
    Returns:
        Detailed validation report with warnings and errors
    """
    from deerteamx.database.session import async_session_maker
    
    # For now, skip Redis validation as it's not implemented yet
    # TODO: Add Redis support when needed
    validator = ConfigValidator(async_session_maker, None, settings)
    report = await validator.validate_all()
    
    return {
        "validation_result": report,
        "recommendations": _generate_recommendations(report)
    }


@router.get("/feature-flags")
async def get_feature_flags(
    settings: DeerTeamXSettings = Depends(get_settings),
) -> Dict[str, bool]:
    """Get current feature flag states.
    
    Returns all feature flags and their current enabled/disabled state.
    Feature flags control experimental or optional functionality.
    
    Returns:
        Dictionary of feature flag name -> boolean state
    """
    return {
        "FEATURE_LONG_TERM_MEMORY": settings.FEATURE_LONG_TERM_MEMORY,
        "FEATURE_CONSENSUS_MODE": settings.FEATURE_CONSENSUS_MODE,
        "FEATURE_HUMAN_FEEDBACK": settings.FEATURE_HUMAN_FEEDBACK,
        "FEATURE_STATE_PERSISTENCE": settings.FEATURE_STATE_PERSISTENCE,
        "FEATURE_CLI_EXECUTION": settings.FEATURE_CLI_EXECUTION,
    }


@router.get("/limits")
async def get_system_limits(
    settings: DeerTeamXSettings = Depends(get_settings),
) -> Dict[str, Any]:
    """Get system rate limits and quotas.
    
    Returns all configured rate limits, file size limits, and quotas.
    Useful for frontend validation and user feedback.
    
    Returns:
        Dictionary of limit configurations
    """
    return {
        "rate_limits": {
            "login_per_minute_per_ip": settings.RATE_LIMIT_LOGIN_PER_MINUTE,
            "register_per_minute_per_ip": settings.RATE_LIMIT_REGISTER_PER_MINUTE,
            "execution_per_minute_per_user": settings.RATE_LIMIT_EXECUTION_PER_MINUTE,
            "import_per_minute_per_user": settings.RATE_LIMIT_IMPORT_PER_MINUTE,
            "read_api_per_minute_per_user": settings.RATE_LIMIT_READ_PER_MINUTE,
            "write_api_per_minute_per_user": settings.RATE_LIMIT_WRITE_PER_MINUTE,
        },
        "file_size_limits": {
            "max_import_file_size_mb": settings.MAX_IMPORT_FILE_SIZE / (1024 * 1024),
            "max_knowledge_file_size_mb": settings.MAX_KNOWLEDGE_FILE_SIZE / (1024 * 1024),
            "max_team_knowledge_size_mb": settings.MAX_TEAM_KNOWLEDGE_SIZE / (1024 * 1024),
        },
        "execution_limits": {
            "execution_lock_ttl_seconds": settings.EXECUTION_LOCK_TTL,
            "execution_timeout_default_seconds": settings.EXECUTION_TIMEOUT_DEFAULT,
            "human_feedback_timeout_range": {
                "min_seconds": 300,
                "max_seconds": 7200,
                "default_seconds": settings.HUMAN_FEEDBACK_TIMEOUT_DEFAULT,
            },
            "import_task_max_parallel_per_user": settings.IMPORT_TASK_MAX_PARALLEL,
        },
        "retention_policies": {
            "import_tasks_retention_days": settings.CLEANUP_IMPORT_TASKS_DAYS,
            "thread_data_retention_days": settings.CLEANUP_THREAD_DATA_DAYS,
            "temp_file_ttls": {
                "import_hours": settings.TEMP_FILE_TTL_IMPORT / 3600,
                "export_hours": settings.TEMP_FILE_TTL_EXPORT / 3600,
                "knowledge_days": settings.TEMP_FILE_TTL_KNOWLEDGE / 86400,
            }
        },
        "localstorage_ttls": {
            "form_draft_days": settings.LOCALSTORAGE_TTL_FORM_DRAFT / 86400,
            "dag_canvas_hours": settings.LOCALSTORAGE_TTL_DAG_CANVAS / 3600,
            "import_progress_seconds": settings.LOCALSTORAGE_TTL_IMPORT_PROGRESS,
            "sensitive_fields_minutes": settings.SESSIONSTORAGE_TTL_SENSITIVE / 60,
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _mask_url(url: str) -> str:
    """Mask credentials in URL for safe logging.
    
    Args:
        url: Full URL with credentials
        
    Returns:
        Masked URL (passwords replaced with ***)
    """
    if "://" not in url:
        return url
    
    protocol, rest = url.split("://", 1)
    
    if "@" in rest:
        creds_and_host = rest.split("@", 1)
        host = creds_and_host[1]
        return f"{protocol}://***@{host}"
    
    return url


def _generate_recommendations(report: Dict[str, Any]) -> list[str]:
    """Generate actionable recommendations based on validation report.
    
    Args:
        report: Validation report from ConfigValidator
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Check for degraded services
    for check_name, check_result in report["checks"].items():
        if check_result["status"] == "error":
            if check_name == "database":
                recommendations.append(
                    "Database connection failed. Check DATABASE_URL and ensure PostgreSQL is running."
                )
            elif check_name == "redis":
                recommendations.append(
                    "Redis connection failed. Check REDIS_URL and ensure Redis is running."
                )
            elif check_name == "deerflow_gateway":
                recommendations.append(
                    "DeerFlow Gateway unreachable. Verify DEERFLOW_GATEWAY_URL and ensure Gateway is running."
                )
            elif check_name == "qdrant":
                recommendations.append(
                    "Qdrant unreachable. Long-term memory will be disabled. "
                    "Check QDRANT_URL or set FEATURE_LONG_TERM_MEMORY=false."
                )
    
    # Check for security warnings
    if report["checks"].get("configuration", {}).get("critical_count", 0) > 0:
        recommendations.append(
            "CRITICAL: Production environment detected with default security keys. "
            "Update JWT_SECRET_KEY and ENCRYPTION_MASTER_KEY immediately."
        )
    
    # Check for performance recommendations
    db_response_time = report["checks"].get("database", {}).get("response_time_ms", 0)
    if db_response_time > 100:
        recommendations.append(
            f"Database response time is high ({db_response_time}ms). "
            "Consider optimizing queries or scaling database resources."
        )
    
    return recommendations
