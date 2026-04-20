"""DeerTeamX Structured Logging Configuration

Provides JSON-formatted structured logging with context propagation.
Integrates with log aggregators (ELK, Datadog, Sentry) for production monitoring.

Features:
- JSON format for machine parsing
- Request ID correlation
- Sensitive data masking
- Log level configuration via environment
- Context propagation (user_id, execution_id, team_id)
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from deerteamx.config.settings import get_settings

settings = get_settings()


class RequestIDFilter(logging.Filter):
    """Inject request_id into all log records within a request scope."""
    
    def __init__(self, request_id: str):
        super().__init__()
        self.request_id = request_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self.request_id
        return True


class ExecutionContextFilter(logging.Filter):
    """Inject execution context (user_id, execution_id, team_id) into log records."""
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ):
        super().__init__()
        self.user_id = user_id
        self.execution_id = execution_id
        self.team_id = team_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        if self.user_id:
            record.user_id = self.user_id
        if self.execution_id:
            record.execution_id = self.execution_id
        if self.team_id:
            record.team_id = self.team_id
        return True


class SensitiveDataFilter(logging.Filter):
    """Mask sensitive data in log messages to prevent leakage."""
    
    SENSITIVE_PATTERNS = [
        ("password", "***MASKED***"),
        ("token", "***MASKED***"),
        ("secret", "***MASKED***"),
        ("api_key", "***MASKED***"),
        ("authorization", "***MASKED***"),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Mask sensitive fields in message
        msg = record.getMessage()
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            if pattern.lower() in msg.lower():
                # Simple masking - in production use regex for better precision
                msg = msg.replace(pattern, replacement, 1)
        
        record.msg = msg
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.
    
    Outputs logs as JSON with consistent fields for log aggregators.
    Compatible with ELK Stack, Datadog, CloudWatch, etc.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.
        
        Args:
            record: Python logging LogRecord
            
        Returns:
            JSON-formatted log line
        """
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }
        
        # Add request context if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add business context if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "execution_id"):
            log_data["execution_id"] = record.execution_id
        if hasattr(record, "team_id"):
            log_data["team_id"] = record.team_id
        
        # Add extra fields from record.__dict__
        for key, value in record.__dict__.items():
            # Skip standard logging fields
            if key.startswith("_") or key in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "taskName", "message", "request_id", "user_id",
                "execution_id", "team_id"
            ):
                continue
            
            # Only add non-standard fields
            if key not in log_data:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development (human-readable).
    
    Only used when LOG_FORMAT=text and APP_ENV=development.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m", # Bold Red
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Build message
        msg = f"{color}[{timestamp}] {record.levelname:<8}{self.RESET} {record.name}: {record.getMessage()}"
        
        # Add request_id if available
        if hasattr(record, "request_id"):
            msg += f" {color}[req:{record.request_id[:8]}]{self.RESET}"
        
        # Add exception info
        if record.exc_info and record.exc_info[0] is not None:
            msg += f"\n{self.formatException(record.exc_info)}"
        
        return msg


def setup_logging(
    app_name: str = "deerteamx",
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> None:
    """Configure application-wide logging.
    
    Args:
        app_name: Application name for logger identification
        log_level: Override LOG_LEVEL from settings (for testing)
        log_format: Override LOG_FORMAT from settings (for testing)
    """
    # Use settings or overrides
    level_str = log_level or settings.LOG_LEVEL
    format_str = log_format or settings.LOG_FORMAT
    
    # Parse log level
    level = getattr(logging, level_str.upper(), logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers (avoid duplicates in reload mode)
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Choose formatter based on format setting
    if format_str.lower() == "json":
        # Production: JSON format for log aggregators
        formatter = JSONFormatter()
    else:
        # Development: Colored text for human readability
        formatter = ColoredFormatter()
    
    console_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(app_name)
    logger.info(
        f"Logging initialized | Level={level_str} | Format={format_str} | App={app_name}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", extra={"user_id": "123"})
    """
    return logging.getLogger(name)


def create_execution_logger(
    execution_id: str,
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> logging.LoggerAdapter:
    """Create a logger pre-configured with execution context.
    
    All log messages will automatically include execution_id, team_id, user_id.
    
    Args:
        execution_id: Execution identifier
        team_id: Team identifier (optional)
        user_id: User identifier (optional)
        
    Returns:
        LoggerAdapter with execution context
        
    Example:
        >>> logger = create_execution_logger("exec-123", team_id="team-456")
        >>> logger.info("Starting execution")  # Automatically includes execution_id
    """
    logger = get_logger(f"deerteamx.execution.{execution_id}")
    
    # Create adapter with extra context
    extra = {
        "execution_id": execution_id,
    }
    if team_id:
        extra["team_id"] = team_id
    if user_id:
        extra["user_id"] = user_id
    
    return logging.LoggerAdapter(logger, extra)
