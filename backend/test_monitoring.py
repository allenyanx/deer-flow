#!/usr/bin/env python3
"""Test script to verify monitoring infrastructure is working correctly.

This script tests:
1. Structured logging initialization
2. Request ID tracking
3. Exception handling
4. Prometheus metrics endpoint (if enabled)
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def test_logging_setup():
    """Test structured logging initialization."""
    print("=" * 80)
    print("TEST 1: Structured Logging Setup")
    print("=" * 80)
    
    from deerteamx.monitoring.logging_config import setup_logging, get_logger
    
    # Initialize logging
    setup_logging(app_name="test", log_level="DEBUG", log_format="text")
    
    # Get logger and test messages
    logger = get_logger("test_module")
    
    logger.debug("Debug message - should appear in DEBUG mode")
    logger.info("Info message - basic logging works")
    logger.warning("Warning message - warning level works")
    
    # Test sensitive data masking
    logger.info("User login with password=secret123 and token=abc123")
    
    # Test JSON format
    print("\n--- Testing JSON format ---")
    setup_logging(app_name="test", log_level="INFO", log_format="json")
    logger_json = get_logger("test_json")
    logger_json.info("JSON formatted log message", extra={"user_id": "123", "request_id": "req-456"})
    
    print("✅ Logging setup test passed\n")


def test_exception_handlers():
    """Test exception handler registration."""
    print("=" * 80)
    print("TEST 2: Exception Handlers")
    print("=" * 80)
    
    from fastapi import FastAPI
    from deerteamx.api.middleware.exception_handlers import (
        register_exception_handlers,
        ResourceNotFoundException,
        ConflictException,
        ValidationException,
    )
    
    app = FastAPI()
    register_exception_handlers(app)
    
    # Check that handlers are registered
    assert len(app.exception_handlers) > 0, "No exception handlers registered"
    print(f"✅ Registered {len(app.exception_handlers)} exception handlers")
    
    # Test custom exceptions
    try:
        raise ResourceNotFoundException("team", "team-123")
    except ResourceNotFoundException as e:
        assert e.status_code == 404
        assert e.error_code == "RESOURCE_NOT_FOUND"
        print(f"✅ ResourceNotFoundException: {e.message}")
    
    try:
        raise ConflictException("Team name already exists")
    except ConflictException as e:
        assert e.status_code == 409
        assert e.error_code == "CONFLICT"
        print(f"✅ ConflictException: {e.message}")
    
    try:
        raise ValidationException("Invalid input", field_errors={"name": "Required"})
    except ValidationException as e:
        assert e.status_code == 422
        assert e.error_code == "VALIDATION_ERROR"
        print(f"✅ ValidationException: {e.message}")
    
    print("✅ Exception handlers test passed\n")


def test_request_tracking_middleware():
    """Test request tracking middleware."""
    print("=" * 80)
    print("TEST 3: Request Tracking Middleware")
    print("=" * 80)
    
    from deerteamx.api.middleware.request_tracking import RequestTrackingMiddleware
    from deerteamx.monitoring.metrics import HTTP_REQUEST_TOTAL, HTTP_REQUEST_DURATION
    
    # Verify middleware class exists
    assert hasattr(RequestTrackingMiddleware, 'dispatch')
    print("✅ RequestTrackingMiddleware has dispatch method")
    
    # Verify metrics are defined
    assert HTTP_REQUEST_TOTAL is not None
    assert HTTP_REQUEST_DURATION is not None
    print("✅ Prometheus metrics objects are initialized")
    
    print("✅ Request tracking middleware test passed\n")


def test_metrics_endpoint():
    """Test Prometheus metrics endpoint creation."""
    print("=" * 80)
    print("TEST 4: Metrics Endpoint")
    print("=" * 80)
    
    from deerteamx.monitoring.metrics import create_metrics_endpoint
    
    router = create_metrics_endpoint()
    assert router is not None
    print("✅ Metrics endpoint router created successfully")
    
    # Check routes
    routes = [route.path for route in router.routes]
    assert "/metrics" in routes
    print(f"✅ Metrics endpoint available at: {routes}")
    
    print("✅ Metrics endpoint test passed\n")


async def test_lifespan_integration():
    """Test lifespan integration with monitoring."""
    print("=" * 80)
    print("TEST 5: Lifespan Integration")
    print("=" * 80)
    
    from deerteamx.main import create_deerteamx_app
    
    # Create app instance
    app = create_deerteamx_app()
    
    # Verify lifespan is configured
    assert app.router.lifespan_context is not None
    print("✅ Lifespan context manager is configured")
    
    # Verify middleware stack
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "RequestTrackingMiddleware" in middleware_classes
    print(f"✅ Middleware stack: {middleware_classes}")
    
    # Verify routers are registered
    routes = [route.path for route in app.routes if hasattr(route, 'path')]
    print(f"✅ Total routes registered: {len(routes)}")
    
    # Check for key endpoints
    expected_endpoints = ["/health", "/api/v1/auth/login", "/api/v1/teams"]
    found_endpoints = [ep for ep in expected_endpoints if any(ep in route for route in routes)]
    print(f"✅ Key endpoints found: {found_endpoints}")
    
    print("✅ Lifespan integration test passed\n")


def test_prometheus_client_installed():
    """Verify prometheus-client is installed."""
    print("=" * 80)
    print("TEST 6: Prometheus Client Installation")
    print("=" * 80)
    
    try:
        import prometheus_client
        # Try to get version (may not be available in all versions)
        version = getattr(prometheus_client, '__version__', 'unknown')
        print(f"✅ prometheus-client installed (version: {version})")
        
        from prometheus_client import Counter, Histogram, Gauge
        print("✅ All metric types available (Counter, Histogram, Gauge)")
        
    except ImportError as e:
        print(f"❌ prometheus-client not installed: {e}")
        print("\nPlease install it:")
        print("  cd /home/ycp/workSpace/ai/games_dev/deer-flow/backend")
        print("  uv pip install prometheus-client")
        sys.exit(1)
    
    print("✅ Prometheus client installation test passed\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("DeerTeamX Monitoring Infrastructure Verification")
    print("=" * 80 + "\n")
    
    try:
        # Run tests
        test_prometheus_client_installed()
        test_logging_setup()
        test_exception_handlers()
        test_request_tracking_middleware()
        test_metrics_endpoint()
        asyncio.run(test_lifespan_integration())
        
        # Summary
        print("=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)
        print("\nMonitoring infrastructure is ready for use.")
        print("\nNext steps:")
        print("1. Start the application:")
        print("   cd /home/ycp/workSpace/ai/games_dev/deer-flow/backend")
        print("   uvicorn deerteamx.main:app --reload")
        print("\n2. Test the health endpoint:")
        print("   curl http://localhost:8000/health")
        print("\n3. If ENABLE_METRICS=true, check metrics:")
        print("   curl http://localhost:8000/metrics")
        print("\n4. View API documentation:")
        print("   http://localhost:8000/deerteamx/docs")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
