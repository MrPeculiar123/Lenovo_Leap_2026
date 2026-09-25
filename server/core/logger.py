"""Structured application logging for the adaptive learning workflow."""

import logging
import os
import sys
from typing import Any


_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",     # Cyan
    logging.INFO: "\033[32m",      # Green
    logging.WARNING: "\033[33m",   # Yellow
    logging.ERROR: "\033[31m",     # Red
    logging.CRITICAL: "\033[35m",  # Magenta
}

# Bold Magenta / Pink for custom PathForge workflow logs ([IRT], [BKT], theta, mastery, etc.)
_WORKFLOW_COLOR = "\033[1;35m"
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s", "%H:%M:%S")
        self.enabled = os.getenv("LOG_COLORS", "1").strip().lower() not in {"0", "false", "no", "off"}

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if not self.enabled:
            return message

        # Force Bright Pink / Magenta for all custom PathForge logs ([IRT], [BKT], theta, etc.)
        if record.name == "learning_navigator" or any(
            tag in record.getMessage() for tag in ["[IRT]", "[BKT]", "[DAG]", "[RAG]", "[LLM]"]
        ):
            color = _WORKFLOW_COLOR
        else:
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
    # Default to DEBUG so [IRT], [BKT], and [DAG] updates are never filtered out
    root.setLevel(os.getenv("LOG_LEVEL", "DEBUG").upper())


configure_logging()
logger = logging.getLogger("learning_navigator")


def workflow_log(level: int, event: str, **fields: Any) -> None:
    """Log a bounded, structured workflow event without learner content."""
    details = " ".join(f"{key}={value!r}" for key, value in fields.items() if value is not None)
    logger.log(level, "%s%s", event, f" {details}" if details else "")


__all__ = ["logger", "workflow_log", "configure_logging"]