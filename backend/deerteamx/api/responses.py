"""Unified Response Wrapper for API Consistency

Wraps all API responses in a standard format:
{
    "data": {...},
    "message": "Success",
    "timestamp": "2026-04-19T10:00:00Z"
}

This ensures consistency with API_REFERENCE.md specifications.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    
    data: Any = Field(..., description="Response data payload")
    message: str = Field(default="Success", description="Human-readable message")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp"
    )


def wrap_response(data: Any, message: str = "Success") -> dict:
    """Wrap response data in standard format.
    
    Args:
        data: Response data (dict, list, or any serializable object)
        message: Optional success message
        
    Returns:
        Standardized response dictionary
    """
    return {
        "data": data,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
