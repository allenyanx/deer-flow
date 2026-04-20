"""FastAPI Dependency Injection Center

Provides reusable dependencies for authentication, authorization, database sessions,
and distributed locks.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.database.session import get_db
from deerteamx.api.middleware.auth import decode_token
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
    db: AsyncSession = Depends(get_db),
) -> User:
    """Parse JWT token and return current user object.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User object from database
        
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    try:
        # Extract and decode token
        token = credentials.credentials
        payload = decode_token(token)
        
        # Extract user_id from payload
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="UNAUTHORIZED",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Convert to UUID
        user_id = UUID(user_id_str)
        
        # Query user from database
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="UNAUTHORIZED",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
    from fastapi import Path
    
    async def check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        resource_id: str = Path(..., alias=resource_id_param),
    ):
        # Query resource from database by ID
        result = await db.execute(
            select(resource_model).where(
                getattr(resource_model, resource_model.__table__.primary_key.columns.keys()[0].name) == resource_id
            )
        )
        resource = result.scalar_one_or_none()
        
        # Check if resource exists (404 if not)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RESOURCE_NOT_FOUND",
            )
        
        # Special handling for system templates (creator_id NULL or scope='system')
        if hasattr(resource, 'scope') and getattr(resource, 'scope', None) == 'system':
            return resource
        
        # Verify creator_id == user.id
        if hasattr(resource, 'creator_id'):
            if resource.creator_id != user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="NOT_RESOURCE_OWNER",
                )
        
        return resource
    
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
