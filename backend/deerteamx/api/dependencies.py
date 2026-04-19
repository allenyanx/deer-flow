"""FastAPI Dependency Injection Center

Provides reusable dependencies for authentication, authorization, database sessions,
and distributed locks.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.database.session import get_db
from deerteamx.config.settings import get_settings
from deerteamx.models.base import User

# Security scheme for JWT Bearer tokens
security = HTTPBearer()

# Permission matrix (from API_REFERENCE.md Appendix A)
PERMISSION_MATRIX = {
    # Team operations
    "team:list": ["developer", "researcher", "enthusiast"],
    "team:create": ["developer", "enthusiast"],
    "team:edit": ["developer", "enthusiast"],
    "team:delete": ["developer", "enthusiast"],
    "team:execute": ["developer", "researcher", "enthusiast"],
    "team:import": ["developer", "enthusiast"],
    
    # Template operations
    "template:list": ["developer", "researcher", "enthusiast"],
    "template:use": ["developer", "researcher", "enthusiast"],
    "template:create": ["developer", "enthusiast"],
    "template:edit": ["developer", "enthusiast"],
    "template:delete": ["developer", "enthusiast"],
    
    # Export
    "export:result": ["developer", "researcher", "enthusiast"],
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Parse JWT token and return current user object.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User object from database
        
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    # TODO: Implement JWT parsing and user lookup
    # 1. Extract token from credentials
    # 2. Decode JWT with SECRET_KEY
    # 3. Extract user_id from payload
    # 4. Query user from database (with caching)
    # 5. Return user object
    pass


def require_permission(permission: str):
    """Permission check dependency: verify role has specified permission.
    
    Usage:
        @router.post("/teams")
        async def create_team(user: User = Depends(require_permission("team:create"))):
            ...
    
    Args:
        permission: Permission code (e.g., "team:create")
        
    Returns:
        Dependency function that checks user's role against PERMISSION_MATRIX
    """
    async def check(user: User = Depends(get_current_user)):
        allowed_roles = PERMISSION_MATRIX.get(permission, [])
        if user.role_type not in allowed_roles:
            raise HTTPException(status_code=403, detail="FORBIDDEN")
        return user
    return Depends(check)


def require_owner(resource_model, resource_id_param: str = "team_id"):
    """Resource ownership check: ensure target belongs to current user.
    
    Usage:
        @router.put("/teams/{team_id}")
        async def update_team(
            team: Team = Depends(require_owner(Team, "team_id")),
        ):
            ...
    
    Args:
        resource_model: SQLAlchemy model class
        resource_id_param: Path parameter name for resource ID
        
    Returns:
        Dependency function that verifies creator_id == current_user.id
    """
    async def check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        # resource_id would be extracted from path parameters
    ):
        # TODO: Implement ownership verification
        # 1. Query resource from database by ID
        # 2. Check if resource exists (404 if not)
        # 3. Special handling for system templates (creator_id NULL = readable by all)
        # 4. Verify creator_id == user.id
        # 5. Return resource if authorized
        pass
    return Depends(check)


async def get_redis():
    """Get Redis connection for distributed locks and caching.
    
    Returns:
        Async Redis client instance
    """
    # TODO: Initialize and return Redis connection
    # 1. Create Redis connection from settings.REDIS_URL
    # 2. Return async Redis client
    pass


async def get_lock_manager():
    """Get distributed lock manager instance.
    
    Returns:
        DistributedLockManager instance for Redis-based locking
    """
    # TODO: Initialize and return lock manager
    # 1. Get Redis connection
    # 2. Create DistributedLockManager instance
    # 3. Return manager
    pass
