"""Authentication and Authorization API Routes

Implements JWT-based authentication with bcrypt password hashing,
role-based access control (RBAC), and rate limiting.
"""

import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from deerteamx.api.schemas.team_schemas import (
    LoginRequest,
    RegisterRequest,
    RoleUpdateRequest,
    TokenResponse,
    UserInfo,
    PermissionMatrixResponse,
)
from deerteamx.api.responses import APIResponse
from deerteamx.database.session import get_db
from deerteamx.models.base import User
from deerteamx.api.middleware.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from deerteamx.api.dependencies import get_current_user, PERMISSION_MATRIX
from deerteamx.api.middleware.rate_limiter import check_rate_limit
from deerteamx.config.settings import get_settings
from deerteamx.api.responses import wrap_response

settings = get_settings()

router = APIRouter(
    prefix="/auth",
    tags=["deerteamx-auth"],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}},
)


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Register a new user account.
    
    Args:
        data: Registration request with username, password, and optional email
        request: FastAPI request object (for rate limiting)
        db: Database session
        
    Returns:
        JWT access token, refresh token, and user info
        
    Raises:
        HTTPException: 409 if username already exists
        HTTPException: 422 if validation fails
        HTTPException: 429 if rate limit exceeded
    """
    # Rate limiting check (by IP)
    await check_rate_limit(
        request,
        "register",
        settings.RATE_LIMIT_REGISTER_PER_MINUTE,
        60,
    )
    
    # Check username uniqueness
    result = await db.execute(
        select(User).where(User.username == data.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="USERNAME_ALREADY_EXISTS",
        )
    
    # Hash password with bcrypt
    password_hash = hash_password(data.password)
    
    # Create user in database (default role: developer)
    new_user = User(
        username=data.username,
        password_hash=password_hash,
        email=data.email,
        role_type="developer",
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate JWT tokens
    access_token = create_access_token(
        user_id=str(new_user.user_id),
        role_type=new_user.role_type,
    )
    refresh_token = create_refresh_token(user_id=str(new_user.user_id))
    
    # Build user info
    user_info = UserInfo(
        id=new_user.user_id,
        username=new_user.username,
        role_type=new_user.role_type,
        created_at=new_user.created_at,
    )
    
    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_info,
    )
    
    return wrap_response(token_data.model_dump())


@router.post("/login", response_model=APIResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Authenticate user and return JWT tokens.
    
    Args:
        data: Login credentials
        request: FastAPI request object (for rate limiting)
        db: Database session
        
    Returns:
        JWT access token, refresh token, and user info
        
    Raises:
        HTTPException: 401 if credentials are invalid
        HTTPException: 429 if rate limit exceeded
    """
    # Rate limiting check (by IP)
    await check_rate_limit(
        request,
        "login",
        settings.RATE_LIMIT_LOGIN_PER_MINUTE,
        60,
    )
    
    # Query user by username
    result = await db.execute(
        select(User).where(User.username == data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Generic error message to prevent username enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )
    
    # Verify password with bcrypt
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )
    
    # Generate JWT tokens
    access_token = create_access_token(
        user_id=str(user.user_id),
        role_type=user.role_type,
    )
    refresh_token = create_refresh_token(user_id=str(user.user_id))
    
    # Build user info
    user_info = UserInfo(
        id=user.user_id,
        username=user.username,
        role_type=user.role_type,
        created_at=user.created_at,
    )
    
    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_info,
    )
    
    return wrap_response(token_data.model_dump())


@router.put("/users/me/role", response_model=APIResponse)
async def update_role(
    data: RoleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update current user's role type.
    
    Args:
        data: New role type
        user: Current authenticated user
        db: Database session
        
    Returns:
        New JWT access token with updated role
        
    Side Effects:
        - Updates user role in database
        - Frontend should refetch permissions with new token
        
    Raises:
        HTTPException: 400 if role_type is invalid
    """
    # Validate role_type
    valid_roles = ["developer", "researcher", "enthusiast"]
    if data.role_type not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role type. Must be one of: {valid_roles}",
        )
    
    # Update user in database
    user.role_type = data.role_type
    user.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(user)
    
    # Generate new JWT token with updated role
    access_token = create_access_token(
        user_id=str(user.user_id),
        role_type=user.role_type,
    )
    refresh_token = create_refresh_token(user_id=str(user.user_id))
    
    # Build user info
    user_info = UserInfo(
        id=user.user_id,
        username=user.username,
        role_type=user.role_type,
        created_at=user.created_at,
    )
    
    # Note: WebSocket broadcast removed for simplicity
    # Can be added later if real-time permission updates are needed
    
    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_info,
    )
    
    return wrap_response(token_data.model_dump())


@router.get("/permissions", response_model=APIResponse)
async def get_permissions(
    user: User = Depends(get_current_user),
) -> Any:
    """Get permission matrix for current user's role.
    
    Args:
        user: Current authenticated user
        
    Returns:
        Permission matrix mapping resources to allowed actions
    """
    # Lookup PERMISSION_MATRIX for role_type
    role_permissions = {}
    
    for permission_code, allowed_roles in PERMISSION_MATRIX.items():
        # Parse permission code: "resource:action"
        parts = permission_code.split(":")
        if len(parts) != 2:
            continue
        
        resource, action = parts
        
        if resource not in role_permissions:
            role_permissions[resource] = {}
        
        role_permissions[resource][action] = user.role_type in allowed_roles
    
    response_data = PermissionMatrixResponse(
        role_type=user.role_type,
        permissions=role_permissions,
    )
    
    return wrap_response(response_data.model_dump())

