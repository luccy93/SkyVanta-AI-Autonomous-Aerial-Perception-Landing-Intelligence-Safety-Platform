"""Structured application logging for SkyVanta AI."""

import logging
import sys
from typing import Optional


def get_logger(name: str = "skyvanta", level: Optional[int] = None) -> logging.Logger:
    """Returns a structured logger with standardized formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level or logging.INFO)
    elif level is not None:
        logger.setLevel(level)
    return logger
