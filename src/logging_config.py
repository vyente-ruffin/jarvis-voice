"""Logging configuration for memory operations with structured JSON logging."""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional


# Default log level
DEFAULT_LOG_LEVEL = "INFO"


def get_log_level() -> int:
    """Get the log level from environment variable.

    Returns:
        Logging level constant (e.g., logging.INFO, logging.DEBUG)
    """
    level_str = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str, logging.INFO)


class JSONFormatter(logging.Formatter):
    """Formatter that outputs log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON string representation of the log record
        """
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        if hasattr(record, "result_count"):
            log_data["result_count"] = record.result_count
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        if hasattr(record, "error_message"):
            log_data["error_message"] = record.error_message
        if hasattr(record, "api_endpoint"):
            log_data["api_endpoint"] = record.api_endpoint

        return json.dumps(log_data)


def configure_logging() -> None:
    """Configure logging with JSON formatter and environment-based log level."""
    log_level = get_log_level()

    # Configure root logger to respect LOG_LEVEL
    logging.basicConfig(level=log_level)

    # Get the memory logger
    logger = logging.getLogger("memory")
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers = []

    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False


def get_memory_logger() -> logging.Logger:
    """Get the configured memory logger.

    Returns:
        Logger instance for memory operations
    """
    logger = logging.getLogger("memory")
    if not logger.handlers:
        configure_logging()
    return logger


@asynccontextmanager
async def log_api_call(
    operation: str,
    user_id: Optional[str] = None,
    api_endpoint: Optional[str] = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Context manager for logging API calls with latency measurement.

    Args:
        operation: Name of the operation being performed
        user_id: Optional user identifier (not logged for privacy in some cases)
        api_endpoint: Optional API endpoint being called

    Yields:
        A dictionary for storing operation results (e.g., result_count)
    """
    logger = get_memory_logger()
    start_time = time.perf_counter()
    result_context: dict[str, Any] = {}

    try:
        yield result_context

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Log successful operation
        extra: dict[str, Any] = {
            "operation": operation,
            "latency_ms": round(latency_ms, 2),
            "status": "success",
        }
        if user_id:
            extra["user_id"] = user_id
        if api_endpoint:
            extra["api_endpoint"] = api_endpoint
        if "result_count" in result_context:
            extra["result_count"] = result_context["result_count"]

        logger.info(
            "Memory API call completed",
            extra=extra,
        )

    except Exception as e:
        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Log failed operation
        extra = {
            "operation": operation,
            "latency_ms": round(latency_ms, 2),
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
        }
        if user_id:
            extra["user_id"] = user_id
        if api_endpoint:
            extra["api_endpoint"] = api_endpoint

        logger.error(
            "Memory API call failed",
            extra=extra,
        )

        # Re-raise the exception for the caller to handle
        raise
