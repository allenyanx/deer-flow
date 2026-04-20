"""Authentication Middleware and JWT Utilities

Provides JWT token creation, validation, and password hashing utilities.
Implements the authentication layer for DeerTeamX API.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError

from deerteamx.config.settings import get_settings

settings = get_settings()


def hash_password(password: str, rounds: Optional[int] = None) -> str:
    """Hash password using bcrypt.
    
    Args:
        password: Plain text password
        rounds: Bcrypt rounds (default from settings)
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("mysecretpassword")
        >>> print(hashed)  # $2b$12$...
    """
    if rounds is None:
        rounds = settings.BCRYPT_ROUNDS
    
    salt = bcrypt.gensalt(rounds=rounds)
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Previously hashed password
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> verify_password("mysecretpassword", hashed)
        True
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    user_id: str,
    role_type: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token.
    
    Args:
        user_id: User identifier (UUID string)
        role_type: User role type (developer/researcher/enthusiast)
        expires_delta: Token expiration time (default from settings)
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token = create_access_token("user-uuid", "developer")
        >>> print(token)  # eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": user_id,
        "role_type": role_type,
        "exp": expire,
        "type": "access",
    }
    
    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token.
    
    Args:
        user_id: User identifier (UUID string)
        expires_delta: Token expiration time (default from settings)
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    
    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload dictionary
        
    Raises:
        JWTError: If token is invalid or expired
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return payload


def verify_token_type(token: str, expected_type: str) -> dict:
    """Verify token type and decode.
    
    Args:
        token: JWT token string
        expected_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)
    
    if payload.get("type") != expected_type:
        raise JWTError(f"Invalid token type. Expected '{expected_type}'")
    
    return payload
