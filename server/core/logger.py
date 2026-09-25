"""Structured application logging for the adaptive learning workflow."""

import logging
import os
import sys
from typing import Any


_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[35m",
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s", "%H:%M:%S")
        self.enabled = os.getenv("LOG_COLORS", "1").strip().lower() not in {"0", "false", "no", "off"}

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        # Enable color whenever LOG_COLORS=1 (ignoring isatty check for Docker)
        if not self.enabled:
            return message
        color = _LEVEL_COLORS.get(record.levelno, "")
        return f"{color}{message}{_RESET}" if color else message


def configure_logging() -> None:
    """Configure one concise console handler without duplicating uvicorn handlers."""
    root = logging.getLogger()
    if any(getattr(handler, "_learning_navigator_handler", False) for handler in root.handlers):
        return

    handler = logging.StreamHandler()
    handler._learning_navigator_handler = True
    handler.setFormatter(_ColorFormatter())
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


configure_logging()
logger = logging.getLogger("learning_navigator")


def workflow_log(level: int, event: str, **fields: Any) -> None:
    """Log a bounded, structured workflow event without learner content."""
    details = " ".join(f"{key}={value!r}" for key, value in fields.items() if value is not None)
    logger.log(level, "%s%s", event, f" {details}" if details else "")


__all__ = ["logger", "workflow_log", "configure_logging"]
