"""Logging setup and configuration."""

import logging
import sys
from typing import Optional

import structlog
from structlog.types import Processor

from shared.config import LoggingConfig, get_config


def setup_logging(
    service_name: Optional[str] = None,
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Set up structured logging for the application.

    Args:
        service_name: Name of the service (defaults to config value).
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Log format ("json" or "text").

    Returns:
        Configured logger instance.
    """
    config = get_config()
    service_name = service_name or config.logging.service_name
    log_level = log_level or config.logging.level
    log_format = log_format or config.logging.format

    # Convert string level to logging level
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure processors based on format
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable format for development
        processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Get logger
    logger = structlog.get_logger(service_name)

    # Also configure standard logging for libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    return logger


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name (defaults to service name from config).

    Returns:
        Bound logger instance.
    """
    config = get_config()
    logger_name = name or config.logging.service_name
    return structlog.get_logger(logger_name)

