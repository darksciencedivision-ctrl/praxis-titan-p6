from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator, Tuple


@contextmanager
def measure(label: str = "") -> Iterator[Tuple[str, float]]:
    """
    Context manager to measure elapsed time in seconds.

    Usage:
        with measure("numeric") as (_, dt):
            ...
    """
    start = time.perf_counter()
    yield (label, 0.0)  # initial dummy value
    end = time.perf_counter()
    elapsed = end - start
    # This helper is mainly here for future use.


def now() -> float:
    return time.perf_counter()


def elapsed(start: float) -> float:
    return time.perf_counter() - start
