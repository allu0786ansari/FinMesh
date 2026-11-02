"""Real service processes for X7 (week 17): start, kill, restart, measure.

Each service is a uvicorn process on 127.0.0.1 running one of the factories in
:mod:`finmesh.services.run`; secrets reach it through its environment only. ``kill``
is abrupt (SIGKILL: no shutdown handlers run), as in a crash. Peak memory (VmHWM) and
CPU time come from ``/proc``, so the resource benchmark needs Linux (WSL counts).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx2


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def proc_resources(pid: int) -> dict[str, float | None]:
    """Peak resident memory (MB) and CPU seconds of a live process, or None off Linux."""
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    except OSError:
        return {"peak_rss_mb": None, "cpu_s": None}
    hwm = next((int(x.split()[1]) for x in status.splitlines() if x.startswith("VmHWM:")), 0)
    ticks = os.sysconf("SC_CLK_TCK")
    cpu = (int(stat[11]) + int(stat[12])) / ticks  # utime + stime (fields 14 and 15)
    return {"peak_rss_mb": round(hwm / 1024, 1), "cpu_s": round(cpu, 2)}


class Service:
    def __init__(self, name: str, factory: str, env: dict[str, str], log_dir: Path) -> None:
        self.name, self.factory, self.env = name, factory, dict(env)
        self.port = free_port()
        self.proc: subprocess.Popen[bytes] | None = None
        self.log = log_dir / f"{name}.log"
        self.starts = 0
        self.last: dict[str, float | None] = {"peak_rss_mb": None, "cpu_s": None}

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self, overrides: dict[str, str] | None = None, timeout: float = 300.0) -> float:
        """Start and wait until healthy; returns the seconds it took. ``overrides`` add to the
        service's environment for this start only."""
        env = {**os.environ, **self.env, **(overrides or {})}
        t0 = time.perf_counter()
        with self.log.open("ab") as log:
            self.proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "--factory", self.factory, "--host",
                 "127.0.0.1", "--port", str(self.port), "--log-level", "warning"],
                env=env, stdout=log, stderr=log,
            )  # fmt: skip
        self.starts += 1
        with httpx2.Client(base_url=self.url, timeout=2) as http:
            while True:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"{self.name} exited at start; see {self.log}")
                try:
                    if http.get("/v1/health").status_code == 200:
                        return time.perf_counter() - t0
                except httpx2.TransportError:
                    pass
                if time.perf_counter() - t0 > timeout:
                    raise TimeoutError(f"{self.name} not healthy after {timeout:.0f} s")
                time.sleep(0.1)

    def measure(self) -> dict[str, float | None]:
        if self.proc is not None and self.proc.poll() is None:
            self.last = proc_resources(self.proc.pid)
        return self.last

    def kill(self) -> None:
        """An abrupt crash: SIGKILL, no shutdown handlers."""
        if self.proc is not None and self.proc.poll() is None:
            self.measure()
            self.proc.kill()
            self.proc.wait(timeout=30)

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.measure()
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=30)

    def restart(self, **overrides: str) -> float:
        self.kill()
        return self.start(overrides)

    def __enter__(self) -> Service:
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop()


__all__ = ["Service", "free_port", "proc_resources"]
