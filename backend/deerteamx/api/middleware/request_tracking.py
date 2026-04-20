"""Request Tracking and Performance Monitoring Middleware

Provides:
- Request ID generation and propagation
- Request timing and performance metrics
- Structured logging with context
- Error tracking and reporting

Usage:
    from deerteamx.api.middleware.request_tracking import (
        RequestTrackingMiddleware,
        add_request_id_middleware,
    )
    
    app.add_middleware(RequestTrackingMiddleware)
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from deerteamx.monitoring.logging_config import (
    ExecutionContextFilter,
    RequestIDFilter,
    get_logger,
)
from deerteamx.monitoring.metrics import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUEST_TOTAL,
    HTTP_REQUEST_IN_PROGRESS,
    HTTP_EXCEPTIONS_TOTAL,
)

logger = get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for request ID tracking and performance monitoring.
    
    Features:
    - Generates unique request_id for each request
    - Injects request_id into response headers
    - Measures request duration
    - Exports Prometheus metrics
    - Adds structured logging context
    """
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with tracking.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response with tracking headers
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Extract route path for metrics (avoid high cardinality)
        route_path = self._get_route_path(request)
        
        # Add request_id to request state for access in handlers
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Increment in-progress counter
        HTTP_REQUEST_IN_PROGRESS.labels(
            method=request.method,
            endpoint=route_path,
        ).inc()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add request_id to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
            
            # Record metrics
            HTTP_REQUEST_TOTAL.labels(
                method=request.method,
                endpoint=route_path,
                status_code=str(response.status_code),
            ).inc()
            
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                endpoint=route_path,
                status_code=str(response.status_code),
            ).observe(duration)
            
            # Log request completion
            log_level = "WARNING" if response.status_code >= 400 else "INFO"
            getattr(logger, log_level.lower())(
                f"{request.method} {request.url.path} | "
                f"status={response.status_code} | "
                f"duration={duration * 1000:.2f}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            return response
            
        except Exception as exc:
            # Calculate duration even for errors
            duration = time.time() - start_time
            
            # Record exception metrics
            HTTP_EXCEPTIONS_TOTAL.labels(
                exception_type=type(exc).__name__,
                endpoint=route_path,
            ).inc()
            
            # Log error
            logger.error(
                f"{request.method} {request.url.path} | "
                f"error={type(exc).__name__} | "
                f"duration={duration * 1000:.2f}ms",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "exception": type(exc).__name__,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            # Re-raise exception
            raise
            
        finally:
            # Decrement in-progress counter
            HTTP_REQUEST_IN_PROGRESS.labels(
                method=request.method,
                endpoint=route_path,
            ).dec()
    
    @staticmethod
    def _get_route_path(request: Request) -> str:
        """Extract normalized route path for metrics.
        
        Avoids high cardinality by using route template instead of actual path.
        E.g., /api/v1/teams/team-123 -> /api/v1/teams/{team_id}
        
        Args:
            request: HTTP request
            
        Returns:
            Normalized route path or raw path if route not found
        """
        # Try to get route from request scope
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            return route.path
        
        # Fallback to raw path (not ideal for metrics)
        return request.url.path


def add_request_id_to_logs(request_id: str, **context_kwargs):
    """Add request_id and optional context to current log scope.
    
    This is a convenience function for route handlers that want to
    include request context in their logs.
    
    Args:
        request_id: Unique request identifier
        **context_kwargs: Additional context (user_id, execution_id, etc.)
        
    Example:
        @router.get("/teams/{team_id}")
        async def get_team(request: Request, team_id: str):
            add_request_id_to_logs(
                request.state.request_id,
                team_id=team_id,
                user_id=current_user.id
            )
            logger.info("Fetching team details")
    """
    # Get root logger
    root_logger = get_logger("")
    
    # Add request_id filter
    request_filter = RequestIDFilter(request_id)
    root_logger.addFilter(request_filter)
    
    # Add execution context filter if provided
    if context_kwargs:
        context_filter = ExecutionContextFilter(**context_kwargs)
        root_logger.addFilter(context_filter)


def create_performance_tracker(operation_name: str):
    """Create a context manager for tracking operation performance.
    
    Args:
        operation_name: Name of the operation being tracked
        
    Returns:
        Context manager that records duration
        
    Example:
        with create_performance_tracker("database_query"):
            result = await db.execute(query)
    """
    import contextlib
    
    @contextlib.contextmanager
    def tracker():
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            logger.debug(
                f"Operation '{operation_name}' completed in {duration * 1000:.2f}ms",
                extra={
                    "operation": operation_name,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
    
    return tracker()


# ============================================================================
# Dependency Injection Helpers
# ============================================================================

async def get_request_id(request: Request) -> str:
    """FastAPI dependency to get current request_id.
    
    Usage:
        @router.get("/example")
        async def example(request_id: str = Depends(get_request_id)):
            return {"request_id": request_id}
    """
    return getattr(request.state, "request_id", "unknown")
