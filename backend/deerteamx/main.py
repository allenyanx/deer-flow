"""DeerTeamX FastAPI Application Factory

Creates and configures the DeerTeamX FastAPI application with all routers,
middleware, and lifecycle handlers. This module is designed to be imported
and mounted by the main DeerFlow application or run standalone.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from deerteamx.api.routers import (
    auth_router,
    teams_router,
    executions_router,
    templates_router,
    import_router,
    skills_router,
    health_router,
    websocket_router,
    config_router,
)
from deerteamx.config.settings import get_settings


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
        version="1.0.0",
        docs_url="/deerteamx/docs",
        redoc_url="/deerteamx/redoc",
        openapi_url="/deerteamx/openapi.json",
    )
    
    # Configure CORS
    cors_origins = settings.CORS_ORIGINS.split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers with /api/v1 prefix
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(teams_router, prefix="/api/v1")
    app.include_router(executions_router, prefix="/api/v1")
    app.include_router(templates_router, prefix="/api/v1")
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
