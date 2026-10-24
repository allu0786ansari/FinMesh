"""Helpers for logging resource use on the target 8 GB machine.

Two memory numbers are reported, because they differ a lot here:

* **peak RSS** (``ru_maxrss``) counts file pages that polars memory-maps while
  reading CSV and Parquet. The operating system can drop those pages at any
  time, so peak RSS overstates real memory pressure.
* **peak anonymous memory** (``RssAnon`` in ``/proc/self/status``, sampled
  every 50 ms) is memory the process actually allocated. This is the number to
  compare against the 8 GB budget. Linux and WSL only; ``None`` elsewhere.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_STATUS = Path("/proc/self/status")


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


def _anon_kb() -> int | None:
    try:
        for line in _STATUS.read_text().splitlines():
            if line.startswith("RssAnon:"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


class AnonPeak:
    """Background sampler of peak anonymous memory, in MB."""

    def __init__(self, interval_s: float = 0.05) -> None:
        self.interval_s = interval_s
        self.peak_kb: int | None = _anon_kb()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            kb = _anon_kb()
            if kb is not None:
                self.peak_kb = max(self.peak_kb or 0, kb)
            self._stop.wait(self.interval_s)

    def __enter__(self) -> AnonPeak:
        if self.peak_kb is not None:
            self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()

    @property
    def mb(self) -> float | None:
        return None if self.peak_kb is None else round(self.peak_kb / 1024, 1)


@contextmanager
def timed(record: dict[str, float], key: str) -> Iterator[None]:
    """Record the wall-clock seconds of a block into ``record[key]``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record[key] = round(time.perf_counter() - start, 2)
