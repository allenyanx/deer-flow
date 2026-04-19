"""DeerTeamX Configuration Validator

Provides comprehensive configuration validation and health checks.
Ensures all required services are accessible and configurations are valid
before the application starts accepting requests.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List

import httpx
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates DeerTeamX configuration and service connectivity."""
    
    def __init__(
        self,
        db_session_factory,
        redis_client,
        settings,
    ):
        """Initialize validator with service clients.
        
        Args:
            db_session_factory: SQLAlchemy async session factory
            redis_client: Redis async client
            settings: DeerTeamXSettings instance
        """
        self.db_session_factory = db_session_factory
        self.redis_client = redis_client
        self.settings = settings
    
    async def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks and return comprehensive report.
        
        Returns:
            Dictionary with validation results for each component:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "timestamp": "ISO 8601 timestamp",
                "checks": {
                    "database": {...},
                    "redis": {...},
                    "deerflow_gateway": {...},
                    "qdrant": {...},
                    "configuration": {...}
                },
                "warnings": ["list of warning messages"]
            }
        """
        start_time = time.time()
        checks = {}
        warnings = []
        
        # Run all checks concurrently
        check_tasks = [
            ("database", self._check_database()),
            ("redis", self._check_redis()),
            ("deerflow_gateway", self._check_deerflow_gateway()),
            ("qdrant", self._check_qdrant()),
            ("configuration", self._check_configuration()),
        ]
        
        for name, task in check_tasks:
            try:
                checks[name] = await task
            except Exception as e:
                logger.error(f"Check '{name}' failed with exception: {e}")
                checks[name] = {
                    "status": "error",
                    "error": str(e),
                    "response_time_ms": -1
                }
        
        # Collect warnings from configuration check
        if "configuration" in checks and checks["configuration"].get("warnings"):
            warnings.extend(checks["configuration"]["warnings"])
        
        # Determine overall status
        all_healthy = all(
            check.get("status") == "ok" 
            for check in checks.values()
        )
        any_critical_error = any(
            check.get("status") == "error" and name in ["database", "redis"]
            for name, check in checks.items()
        )
        
        if any_critical_error:
            overall_status = "unhealthy"
        elif not all_healthy:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": overall_status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_ms": elapsed_ms,
            "checks": checks,
            "warnings": warnings
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity."""
        start = time.time()
        try:
            async with self.db_session_factory() as session:
                await session.execute(text("SELECT 1"))
            
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "response_time_ms": response_time_ms,
                "url": self._mask_url(self.settings.DATABASE_URL)
            }
        except Exception as e:
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "error",
                "error": str(e),
                "response_time_ms": response_time_ms
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        start = time.time()
        try:
            await self.redis_client.ping()
            
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "response_time_ms": response_time_ms,
                "url": self._mask_url(self.settings.REDIS_URL)
            }
        except Exception as e:
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "error",
                "error": str(e),
                "response_time_ms": response_time_ms
            }
    
    async def _check_deerflow_gateway(self) -> Dict[str, Any]:
        """Check DeerFlow Gateway connectivity."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(
                    f"{self.settings.DEERFLOW_GATEWAY_URL}/health"
                )
            
            response_time_ms = int((time.time() - start) * 1000)
            status = "ok" if response.status_code == 200 else "error"
            
            return {
                "status": status,
                "response_time_ms": response_time_ms,
                "url": self.settings.DEERFLOW_GATEWAY_URL,
                "http_status": response.status_code
            }
        except Exception as e:
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "error",
                "error": str(e),
                "response_time_ms": response_time_ms
            }
    
    async def _check_qdrant(self) -> Dict[str, Any]:
        """Check Qdrant vector database connectivity."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(
                    f"{self.settings.QDRANT_URL}/healthz"
                )
            
            response_time_ms = int((time.time() - start) * 1000)
            status = "ok" if response.status_code == 200 else "error"
            
            return {
                "status": status,
                "response_time_ms": response_time_ms,
                "url": self.settings.QDRANT_URL,
                "http_status": response.status_code
            }
        except Exception as e:
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "error",
                "error": str(e),
                "response_time_ms": response_time_ms
            }
    
    async def _check_configuration(self) -> Dict[str, Any]:
        """Validate configuration settings and security constraints."""
        warnings = self.settings.validate_all()
        
        # Additional runtime checks
        critical_issues = [w for w in warnings if w.startswith("CRITICAL:")]
        
        if critical_issues:
            status = "error"
        elif warnings:
            status = "warning"
        else:
            status = "ok"
        
        return {
            "status": status,
            "warnings": warnings,
            "critical_count": len(critical_issues),
            "warning_count": len(warnings),
            "environment": self.settings.APP_ENV
        }
    
    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask sensitive information in URLs for logging.
        
        Args:
            url: Full URL with credentials
            
        Returns:
            Masked URL (credentials replaced with ***)
        """
        if "://" not in url:
            return url
        
        protocol, rest = url.split("://", 1)
        
        if "@" in rest:
            creds_and_host = rest.split("@", 1)
            host = creds_and_host[1]
            return f"{protocol}://***@{host}"
        
        return url


async def run_startup_validation(
    db_session_factory,
    redis_client,
    settings,
    fail_on_critical: bool = True,
) -> bool:
    """Run comprehensive validation at application startup.
    
    Args:
        db_session_factory: SQLAlchemy async session factory
        redis_client: Redis async client
        settings: DeerTeamXSettings instance
        fail_on_critical: If True, raise exception on critical failures
        
    Returns:
        True if all checks passed, False otherwise
        
    Raises:
        RuntimeError: If critical checks fail and fail_on_critical=True
    """
    validator = ConfigValidator(db_session_factory, redis_client, settings)
    report = await validator.validate_all()
    
    # Log results
    logger.info(f"Configuration validation completed: {report['status']}")
    logger.info(f"Total elapsed time: {report['elapsed_ms']}ms")
    
    for check_name, check_result in report["checks"].items():
        status_icon = "✅" if check_result["status"] == "ok" else "❌"
        logger.info(
            f"{status_icon} {check_name}: {check_result['status']} "
            f"({check_result.get('response_time_ms', 'N/A')}ms)"
        )
    
    if report["warnings"]:
        logger.warning(f"Found {len(report['warnings'])} warnings:")
        for warning in report["warnings"]:
            logger.warning(f"  - {warning}")
    
    # Check for critical failures
    critical_failures = [
        name for name, result in report["checks"].items()
        if result["status"] == "error" and name in ["database", "redis"]
    ]
    
    if critical_failures and fail_on_critical:
        error_msg = (
            f"Critical service(s) unavailable: {', '.join(critical_failures)}. "
            f"Application cannot start without these services."
        )
        logger.critical(error_msg)
        raise RuntimeError(error_msg)
    
    return report["status"] == "healthy"
