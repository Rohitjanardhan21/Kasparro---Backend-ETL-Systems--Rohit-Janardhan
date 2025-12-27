"""Logging configuration for the application."""

import logging
import sys
from typing import Dict, Any
import structlog
from .config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class RequestLogger:
    """Logger for API requests with context."""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
    
    def log_request(self, method: str, path: str, **kwargs) -> None:
        """Log an API request."""
        self.logger.info(
            "API request",
            method=method,
            path=path,
            **kwargs
        )
    
    def log_response(self, status_code: int, latency_ms: float, **kwargs) -> None:
        """Log an API response."""
        self.logger.info(
            "API response",
            status_code=status_code,
            latency_ms=latency_ms,
            **kwargs
        )