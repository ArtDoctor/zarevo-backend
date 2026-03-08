import logging
import time
from collections.abc import Callable
from typing import TypeVar

_log = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 10
MAX_RETRIES = 3

T = TypeVar("T")


def run_with_retry(
    fn: Callable[[], T],
    max_retries: int = MAX_RETRIES,
    delay_seconds: float = RETRY_DELAY_SECONDS,
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                _log.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.0fs...",
                    attempt + 1,
                    max_retries,
                    e,
                    delay_seconds,
                )
                time.sleep(delay_seconds)
            else:
                raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unexpected retry loop exit")
