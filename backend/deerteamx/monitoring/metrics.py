"""DeerTeamX Prometheus Metrics Exporter

Provides application-level metrics for monitoring and alerting.
Exports metrics in Prometheus exposition format.

Metrics Categories:
- HTTP Request Metrics (latency, status codes, throughput)
- Business Metrics (team creations, executions, imports)
- Infrastructure Metrics (database queries, cache hits, lock contention)
- Error Metrics (exceptions, validation failures)

Usage:
    from deerteamx.monitoring.metrics import (
        HTTP_REQUEST_DURATION,
        TEAM_CREATION_TOTAL,
    )
    
    # In route handler
    with HTTP_REQUEST_DURATION.time():
        # Process request
        pass
    
    TEAM_CREATION_TOTAL.inc()
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response
from fastapi.routing import APIRoute


# ============================================================================
# HTTP Request Metrics
# ============================================================================

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint", "status_code"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUEST_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

HTTP_EXCEPTIONS_TOTAL = Counter(
    "http_exceptions_total",
    "Total HTTP exceptions by type",
    labelnames=["exception_type", "endpoint"],
)

HTTP_REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    labelnames=["method", "endpoint"],
)


# ============================================================================
# Authentication Metrics
# ============================================================================

AUTH_LOGIN_TOTAL = Counter(
    "auth_login_attempts_total",
    "Total login attempts",
    labelnames=["status"],  # success/failure
)

AUTH_REGISTER_TOTAL = Counter(
    "auth_registrations_total",
    "Total user registrations",
    labelnames=["status"],  # success/failure
)

AUTH_TOKEN_REFRESH_TOTAL = Counter(
    "auth_token_refreshes_total",
    "Total token refresh operations",
)


# ============================================================================
# Team Management Metrics
# ============================================================================

TEAM_CREATION_TOTAL = Counter(
    "team_creations_total",
    "Total team creations",
    labelnames=["execution_mode"],  # static/hybrid
)

TEAM_UPDATE_TOTAL = Counter(
    "team_updates_total",
    "Total team updates",
)

TEAM_DELETION_TOTAL = Counter(
    "team_deletions_total",
    "Total team deletions",
)

TEAM_ACTIVE_TOTAL = Gauge(
    "teams_active_total",
    "Number of active (non-deleted) teams",
)


# ============================================================================
# Execution Engine Metrics
# ============================================================================

EXECUTION_TRIGGER_TOTAL = Counter(
    "execution_triggers_total",
    "Total execution triggers",
    labelnames=["team_id"],
)

EXECUTION_COMPLETION_TOTAL = Counter(
    "execution_completions_total",
    "Total execution completions",
    labelnames=["status"],  # completed/failed/cancelled
)

EXECUTION_DURATION_SECONDS = Histogram(
    "execution_duration_seconds",
    "Execution duration in seconds",
    labelnames=["team_id", "status"],
    buckets=[30, 60, 120, 300, 600, 1800, 3600],
)

EXECUTION_ACTIVE_TOTAL = Gauge(
    "executions_active_total",
    "Number of currently running executions",
)

EXECUTION_TOKEN_USAGE = Summary(
    "execution_token_usage",
    "Token usage per execution",
    labelnames=["token_type"],  # input/output
)

EXECUTION_COST_CENTS = Summary(
    "execution_cost_cents",
    "Execution cost in cents",
)


# ============================================================================
# CrewAI Import Metrics
# ============================================================================

IMPORT_TASK_TOTAL = Counter(
    "import_tasks_total",
    "Total CrewAI import tasks",
    labelnames=["status"],  # completed/failed/cancelled
)

IMPORT_TASK_DURATION_SECONDS = Histogram(
    "import_task_duration_seconds",
    "Import task processing duration",
    labelnames=["status"],
    buckets=[1, 5, 10, 30, 60, 120],
)

IMPORT_WARNINGS_TOTAL = Counter(
    "import_warnings_total",
    "Total import warnings generated",
)

IMPORT_ERRORS_TOTAL = Counter(
    "import_errors_total",
    "Total import errors encountered",
)


# ============================================================================
# Template Management Metrics
# ============================================================================

TEMPLATE_CREATION_TOTAL = Counter(
    "template_creations_total",
    "Total template creations",
    labelnames=["scope"],  # system/personal
)

TEMPLATE_USAGE_TOTAL = Counter(
    "template_usages_total",
    "Total template usages (team creation from template)",
)


# ============================================================================
# Infrastructure Metrics
# ============================================================================

DB_QUERY_DURATION_SECONDS = Histogram(
    "database_query_duration_seconds",
    "Database query duration",
    labelnames=["operation"],  # select/insert/update/delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

DB_CONNECTION_POOL_SIZE = Gauge(
    "database_connection_pool_size",
    "Database connection pool size",
)

DB_CONNECTION_POOL_AVAILABLE = Gauge(
    "database_connection_pool_available",
    "Available database connections in pool",
)

REDIS_OPERATION_DURATION_SECONDS = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration",
    labelnames=["operation"],  # get/set/del/ping
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
)

REDIS_CACHE_HIT_TOTAL = Counter(
    "redis_cache_hits_total",
    "Total Redis cache hits",
    labelnames=["cache_type"],
)

REDIS_CACHE_MISS_TOTAL = Counter(
    "redis_cache_misses_total",
    "Total Redis cache misses",
    labelnames=["cache_type"],
)


# ============================================================================
# Distributed Lock Metrics
# ============================================================================

LOCK_ACQUIRE_TOTAL = Counter(
    "locks_acquired_total",
    "Total distributed lock acquisitions",
    labelnames=["resource_type"],  # team/skill/config
)

LOCK_RELEASE_TOTAL = Counter(
    "locks_released_total",
    "Total distributed lock releases",
    labelnames=["status"],  # success/timeout
)

LOCK_CONTENTION_TOTAL = Counter(
    "lock_contention_total",
    "Total lock contention events (failed acquisition)",
    labelnames=["resource_type"],
)

LOCK_HEARTBEAT_ERRORS_TOTAL = Counter(
    "lock_heartbeat_errors_total",
    "Total lock heartbeat failures",
)

LOCK_HOLD_DURATION_SECONDS = Histogram(
    "lock_hold_duration_seconds",
    "Duration locks are held",
    labelnames=["resource_type"],
    buckets=[60, 300, 600, 1800, 3600],
)


# ============================================================================
# Skills Management Metrics
# ============================================================================

SKILLS_BINDING_TOTAL = Counter(
    "skills_bindings_total",
    "Total skill binding operations",
    labelnames=["status"],  # success/failure
)

SKILLS_FILE_LOCK_TIMEOUTS_TOTAL = Counter(
    "skills_file_lock_timeouts_total",
    "Total skills file lock timeouts",
)


# ============================================================================
# WebSocket Metrics
# ============================================================================

WEBSOCKET_CONNECTIONS_TOTAL = Gauge(
    "websocket_connections_active",
    "Number of active WebSocket connections",
)

WEBSOCKET_MESSAGES_SENT_TOTAL = Counter(
    "websocket_messages_sent_total",
    "Total WebSocket messages sent",
    labelnames=["message_type"],
)

WEBSOCKET_CONNECTION_ERRORS_TOTAL = Counter(
    "websocket_connection_errors_total",
    "Total WebSocket connection errors",
)


# ============================================================================
# Background Task Metrics
# ============================================================================

BACKGROUND_TASKS_ACTIVE = Gauge(
    "background_tasks_active",
    "Number of currently running background tasks",
    labelnames=["task_type"],
)

BACKGROUND_TASKS_COMPLETED_TOTAL = Counter(
    "background_tasks_completed_total",
    "Total background tasks completed",
    labelnames=["task_type", "status"],
)


# ============================================================================
# Cleanup Task Metrics
# ============================================================================

IMPORT_TASKS_CLEANED_TOTAL = Counter(
    "import_tasks_cleaned_total",
    "Total import tasks cleaned up",
    labelnames=["status"],
)

THREADS_CLEANED_TOTAL = Counter(
    "threads_cleaned_total",
    "Total DeerFlow threads cleaned up",
)

THREAD_CLEANUP_ERRORS_TOTAL = Counter(
    "thread_cleanup_errors_total",
    "Total thread cleanup errors",
)

TEMP_FILES_CLEANED_TOTAL = Counter(
    "temp_files_cleaned_total",
    "Total temporary files cleaned up",
    labelnames=["type"],
)


# ============================================================================
# FastAPI Metrics Middleware Helper
# ============================================================================

def create_metrics_endpoint() -> APIRoute:
    """Create Prometheus metrics endpoint.
    
    Returns:
        FastAPI route that exposes metrics in Prometheus format
        
    Usage:
        app.include_router(create_metrics_endpoint())
    """
    from fastapi import APIRouter
    
    router = APIRouter()
    
    @router.get("/metrics")
    def metrics():
        """Expose metrics in Prometheus exposition format."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    
    return router


# ============================================================================
# Utility Functions
# ============================================================================

def reset_all_metrics():
    """Reset all metrics (for testing only).
    
    WARNING: Do not use in production!
    """
    collectors = [
        HTTP_REQUEST_DURATION,
        HTTP_REQUEST_TOTAL,
        HTTP_EXCEPTIONS_TOTAL,
        AUTH_LOGIN_TOTAL,
        TEAM_CREATION_TOTAL,
        EXECUTION_TRIGGER_TOTAL,
        IMPORT_TASK_TOTAL,
    ]
    
    for collector in collectors:
        try:
            collector._metrics.clear()
        except AttributeError:
            pass  # Some collectors don't have _metrics attribute
