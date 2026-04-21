"""DeerTeamX FastAPI Application Factory

Creates and configures the DeerTeamX FastAPI application with all routers,
middleware, and lifecycle handlers. This module is designed to be imported
and mounted by the main DeerFlow application or run standalone.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from deerteamx.api.routers import (
    auth_router,
    teams_router,
    executions_router,
    templates_router,
    versions_router,
    import_router,
    skills_router,
    health_router,
    websocket_router,
    config_router,
)
from deerteamx.config.settings import get_settings
from deerteamx.monitoring.logging_config import setup_logging
from deerteamx.monitoring.metrics import create_metrics_endpoint
from deerteamx.api.middleware.request_tracking import RequestTrackingMiddleware
from deerteamx.api.middleware.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    settings = get_settings()
    
    # Initialize structured logging
    setup_logging(
        app_name=settings.APP_NAME,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )
    
    logger = None
    try:
        from deerteamx.monitoring.logging_config import get_logger
        logger = get_logger("deerteamx.startup")
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"Environment: {settings.APP_ENV}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        
        # Run configuration validation (optional - can be disabled for faster startup)
        if settings.APP_ENV == "production":
            logger.info("Running production configuration validation...")
            try:
                from deerteamx.utils.config_validator import run_startup_validation
                from deerteamx.database.session import async_session_maker
                from deerteamx.core.runtime.lock_manager import get_redis_client
                
                redis_client = get_redis_client()
                await run_startup_validation(
                    db_session_factory=async_session_maker,
                    redis_client=redis_client,
                    settings=settings,
                    fail_on_critical=True,
                )
                logger.info("✅ All configuration checks passed")
            except Exception as e:
                logger.critical(f"❌ Configuration validation failed: {e}")
                raise
        
        logger.info("✅ Application startup complete")
        
    except Exception as e:
        if logger:
            logger.critical(f"Application startup failed: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    if logger:
        logger.info("Shutting down application...")
    
    # Cleanup resources
    from deerteamx.database.session import close_db
    await close_db()
    
    if logger:
        logger.info("✅ Application shutdown complete")


def create_deerteamx_app() -> FastAPI:
    """Create and configure the DeerTeamX FastAPI application.
    
    Returns:
        Configured FastAPI application instance with all DeerTeamX routers
    """
    settings = get_settings()
    
    app = FastAPI(
        title="DeerTeamX API",
        description="""
## DeerTeamX - Multi-Agent Team Orchestration Platform

Enterprise-grade team collaboration platform built on top of DeerFlow.

### Features

- **Team Management**: Create and manage multi-agent collaboration workflows
- **Execution Engine**: Trigger and monitor team executions with real-time updates
- **Template Library**: Reusable team configurations for common workflows
- **CrewAI Import**: Seamless migration from CrewAI v0.5-v0.8 configurations
- **RBAC Permissions**: Role-based access control with three user types
- **Version Control**: Semantic versioning with configuration snapshots and diffs
- **Real-time Updates**: WebSocket-based live execution progress tracking

### Architecture

DeerTeamX extends DeerFlow's native capabilities through a zero-intrusion adapter layer,
preserving full compatibility with existing DeerFlow agents, tools, and skills.
        """,
        version=settings.APP_VERSION,
        docs_url="/deerteamx/docs",
        redoc_url="/deerteamx/redoc",
        openapi_url="/deerteamx/openapi.json",
        lifespan=lifespan,
    )
    
    # Configure CORS
    cors_origins = settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request tracking middleware (must be added before other middleware)
    app.add_middleware(RequestTrackingMiddleware)
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register metrics endpoint (if enabled)
    if settings.ENABLE_METRICS:
        metrics_router = create_metrics_endpoint()
        app.include_router(metrics_router)
    
    # Register routers with /api/v1 prefix
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(teams_router, prefix="/api/v1")
    app.include_router(executions_router, prefix="/api/v1")
    app.include_router(templates_router, prefix="/api/v1")
    app.include_router(versions_router, prefix="/api/v1")  # Version management
    app.include_router(import_router, prefix="/api/v1")
    app.include_router(skills_router, prefix="/api/v1")
    app.include_router(config_router, prefix="/api/v1")  # Configuration management
    app.include_router(health_router)  # /health (no prefix for load balancer compatibility)
    app.include_router(websocket_router)  # /ws/global
    
    return app


# Create app instance for standalone testing
app = create_deerteamx_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "deerteamx.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
