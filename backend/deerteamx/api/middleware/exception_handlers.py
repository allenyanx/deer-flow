"""Global Exception Handlers

Provides unified error response formatting and logging.
All exceptions are caught and returned in a consistent format.

Error Response Format:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {...},  // Optional additional context
        "timestamp": "2026-04-20T10:30:00Z",
        "request_id": "uuid-v4"
    }
}
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from deerteamx.monitoring.logging_config import get_logger
from deerteamx.monitoring.metrics import HTTP_EXCEPTIONS_TOTAL

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with FastAPI app.
    
    Args:
        app: FastAPI application instance
        
    Usage:
        from deerteamx.api.middleware.exception_handlers import register_exception_handlers
        register_exception_handlers(app)
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle FastAPI HTTPException.
        
        Args:
            request: HTTP request
            exc: HTTPException instance
            
        Returns:
            JSON response with standardized error format
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log the exception
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
                "error_code": exc.detail if isinstance(exc.detail, str) else "UNKNOWN",
            }
        )
        
        # Build error response
        error_response = {
            "error": {
                "code": exc.detail if isinstance(exc.detail, str) else "HTTP_ERROR",
                "message": str(exc.detail),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            }
        }
        
        # Add headers if provided
        headers = getattr(exc, "headers", {})
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=headers,
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors (Pydantic validation).
        
        Args:
            request: HTTP request
            exc: RequestValidationError instance
            
        Returns:
            JSON response with validation error details
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Extract validation errors
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        # Log validation error
        logger.info(
            f"Validation failed: {len(errors)} error(s)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "validation_errors": errors,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {
                        "errors": errors,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                }
            },
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle Pydantic model validation errors.
        
        Args:
            request: HTTP request
            exc: ValidationError instance
            
        Returns:
            JSON response with validation error details
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        logger.info(
            f"Pydantic validation failed: {len(errors)} error(s)",
            extra={
                "request_id": request_id,
                "validation_errors": errors,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Data validation failed",
                    "details": {"errors": errors},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                }
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all unhandled exceptions.
        
        This is the catch-all handler for unexpected errors.
        
        Args:
            request: HTTP request
            exc: Exception instance
            
        Returns:
            JSON response with generic error message (no internal details exposed)
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log full exception with traceback
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "exception_type": type(exc).__name__,
            }
        )
        
        # Record metrics
        HTTP_EXCEPTIONS_TOTAL.labels(
            exception_type=type(exc).__name__,
            endpoint=request.url.path,
        ).inc()
        
        # Return generic error message (don't expose internals)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                }
            },
        )
    
    @app.exception_handler(PermissionError)
    async def permission_exception_handler(
        request: Request, exc: PermissionError
    ) -> JSONResponse:
        """Handle permission denied errors.
        
        Args:
            request: HTTP request
            exc: PermissionError instance
            
        Returns:
            403 Forbidden response
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.warning(
            f"Permission denied: {str(exc)}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to perform this action",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                }
            },
        )
    
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_exception_handler(
        request: Request, exc: FileNotFoundError
    ) -> JSONResponse:
        """Handle file not found errors.
        
        Args:
            request: HTTP request
            exc: FileNotFoundError instance
            
        Returns:
            404 Not Found response
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.info(
            f"File not found: {str(exc)}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": "The requested file was not found",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                }
            },
        )


# ============================================================================
# Custom Exception Classes
# ============================================================================

class DeerTeamXException(Exception):
    """Base exception for DeerTeamX application.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "APPLICATION_ERROR",
        status_code: int = 500,
        details: Dict[str, Any] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ResourceNotFoundException(DeerTeamXException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
            }
        )


class ConflictException(DeerTeamXException):
    """Raised when there is a resource conflict (e.g., duplicate name)."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details,
        )


class LockedException(DeerTeamXException):
    """Raised when a resource is locked (e.g., team executing)."""
    
    def __init__(self, resource_type: str, resource_id: str, lock_owner: str = None):
        details = {
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
        if lock_owner:
            details["lock_owner"] = lock_owner
        
        super().__init__(
            message=f"{resource_type} is currently locked and cannot be modified",
            error_code="RESOURCE_LOCKED",
            status_code=423,
            details=details,
        )


class ValidationException(DeerTeamXException):
    """Raised when business logic validation fails."""
    
    def __init__(self, message: str, field_errors: Dict[str, str] = None):
        details = {}
        if field_errors:
            details["field_errors"] = field_errors
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )
