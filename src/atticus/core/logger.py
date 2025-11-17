"""
Logging configuration for Project Atticus.

This module provides a centralized logging system using loguru with support
for file rotation, colored console output, and structured logging.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from atticus.core.config import get_config

# Remove default handler
logger.remove()


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "500 MB",
    retention: str = "10 days",
    console_colors: bool = True,
) -> None:
    """
    Set up the logger with console and file handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, file logging is disabled)
        rotation: Log file rotation size
        retention: Log file retention period
        console_colors: Enable colored console output
    """
    # Console handler
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    if not console_colors:
        console_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )

    logger.add(
        sys.stdout,
        format=console_format,
        level=log_level,
        colorize=console_colors,
        backtrace=True,
        diagnose=True,
    )

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{extra[request_id]} | "
            "{message}"
        )

        logger.add(
            log_file,
            format=file_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            enqueue=True,  # Thread-safe
        )


def get_logger(name: Optional[str] = None):
    """
    Get a logger instance.

    Args:
        name: Optional logger name (usually __name__)

    Returns:
        Logger instance
    """
    try:
        config = get_config()

        # Initialize logger if not already done
        if not logger._core.handlers:
            setup_logger(
                log_level=config.logging.level,
                log_file=config.logging.file_path if config.logging.file_enabled else None,
                rotation=config.logging.rotation,
                retention=config.logging.retention,
                console_colors=config.logging.console_colors,
            )
    except Exception:
        # Fallback to basic configuration
        setup_logger()

    if name:
        return logger.bind(name=name)
    return logger


# Create a default logger instance
log = get_logger("atticus")
