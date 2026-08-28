"""Structured deployment logging adapter and JSON formatter for cloud containers."""

import json
import logging
import sys
import time
from typing import Any, Dict, Optional


class JSONDeploymentFormatter(logging.Formatter):
    """Formats log records as single-line structured JSON objects for observability engines."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt) if self.datefmt else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "skyvanta-deployment",
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include structured extra fields if present
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class DeploymentLogger:
    """Configures deployment logging based on environment tier."""

    @staticmethod
    def configure_logging(
        level: str = "INFO",
        json_format: bool = False,
        logger_name: Optional[str] = "skyvanta.deployment",
    ) -> logging.Logger:
        """Initializes and returns a configured logger instance.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR).
            json_format: If True, uses JSON formatter; otherwise standard text.
            logger_name: Specific logger namespace.

        Returns:
            logging.Logger instance.
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Clear existing handlers to prevent duplication
        if logger.hasHandlers():
            logger.handlers.clear()

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))

        if json_format:
            handler.setFormatter(JSONDeploymentFormatter())
        else:
            formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False
        return logger
