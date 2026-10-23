"""Small helpers for logging resource use on the target 8 GB machine."""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager


def peak_rss_mb() -> float | None:
    """Peak resident memory of this process in MB, or None where unsupported (Windows)."""
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports kilobytes, macOS reports bytes.
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return round(peak / divisor, 1)


@contextmanager
def timed(record: dict[str, float], key: str) -> Iterator[None]:
    """Record the wall-clock seconds of a block into ``record[key]``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record[key] = round(time.perf_counter() - start, 2)
