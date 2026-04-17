"""
logger.py - Centralized logging configuration.

Sets up both file and console handlers with color support
and a consistent format across all modules.
"""

import logging
import os
from pathlib import Path

import colorlog


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger with the given name.

    Uses colorlog for console output and a plain file handler
    if LOG_FILE is configured in the environment.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured Logger instance.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers when the logger is re-used
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    # ── Console handler (colorized) ──────────────────────────────────
    console_fmt = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)-8s]%(reset)s "
        "%(cyan)s%(name)s%(reset)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG":    "white",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # ── File handler (plain text) ────────────────────────────────────
    log_file = os.getenv("LOG_FILE", "logs/scraper.log")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger
