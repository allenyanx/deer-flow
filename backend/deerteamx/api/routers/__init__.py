"""API Routers Package - Export all router instances"""

from deerteamx.api.routers.auth import router as auth_router
from deerteamx.api.routers.teams import router as teams_router
from deerteamx.api.routers.executions import router as executions_router
from deerteamx.api.routers.templates import router as templates_router
from deerteamx.api.routers.import_export import router as import_router
from deerteamx.api.routers.skills import router as skills_router
from deerteamx.api.routers.health import router as health_router
from deerteamx.api.routers.websocket import router as websocket_router
from deerteamx.api.routers.config import router as config_router

__all__ = [
    "auth_router",
    "teams_router",
    "executions_router",
    "templates_router",
    "import_router",
    "skills_router",
    "health_router",
    "websocket_router",
    "config_router",
]
