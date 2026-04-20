"""Simple Rate Limiting Middleware

Provides basic rate limiting using in-memory storage.
For production, replace with Redis-based implementation.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """In-memory rate limiter (for development/testing only).
    
    WARNING: This is NOT suitable for production or multi-instance deployments.
    Use Redis-based rate limiting instead.
    """
    
    def __init__(self):
        # Store: {key: [(timestamp, count), ...]}
        self._store: Dict[str, list] = defaultdict(list)
    
    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is within rate limit.
        
        Args:
            key: Rate limit key (e.g., "login:192.168.1.1")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old entries
        self._store[key] = [
            ts for ts in self._store[key] if ts > window_start
        ]
        
        # Check limit
        if len(self._store[key]) >= max_requests:
            return False
        
        # Record request
        self._store[key].append(now)
        return True
    
    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in current window.
        
        Args:
            key: Rate limit key
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Number of remaining requests
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old entries
        self._store[key] = [
            ts for ts in self._store[key] if ts > window_start
        ]
        
        remaining = max_requests - len(self._store[key])
        return max(0, remaining)


# Global rate limiter instance (for development)
rate_limiter = InMemoryRateLimiter()


async def check_rate_limit(
    request: Request,
    key_prefix: str,
    max_requests: int,
    window_seconds: int,
):
    """Check rate limit and raise HTTP 429 if exceeded.
    
    Args:
        request: FastAPI request object
        key_prefix: Rate limit key prefix (e.g., "login")
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        
    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Extract client IP
    client_ip = request.client.host if request.client else "unknown"
    key = f"{key_prefix}:{client_ip}"
    
    # Check rate limit
    if not rate_limiter.check_rate_limit(key, max_requests, window_seconds):
        remaining = rate_limiter.get_remaining(key, max_requests, window_seconds)
        reset_time = int(time.time()) + window_seconds
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="RATE_LIMIT_EXCEEDED",
            headers={
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(window_seconds),
            },
        )
