"""Small synchronous resilience helpers for optional external services."""

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_call(operation: Callable[[], T], retries: int = 2, delay_seconds: float = 0.25) -> T:
    """Retry transient service calls without hiding the final exception."""
    attempts = max(1, retries + 1)
    for attempt in range(attempts):
        try:
            return operation()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(delay_seconds * (attempt + 1))
    raise RuntimeError("retry_call exhausted without returning")