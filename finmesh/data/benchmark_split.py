"""A25 P6: AMLworld's published benchmark split, as a dataset of its own (``<source>-FULL``).

The benchmark (Altman et al., NeurIPS 2023; Egressy et al., AAAI 2024; the IBM Multi-GNN
code) orders transactions by time and splits them **by day** into train, validation and
test, choosing the two day boundaries whose shares come closest to 60/20/20 (the smallest
largest relative error). Every transaction is used, including the sparse tail after the
dense period that our G0 window leaves out.

``<source>-FULL`` points at the source's raw files (symbolic links; a copy where links are
not allowed) and goes through the usual pipeline (``week1``, ``g0``, ``labels``,
``features`` and ``features --view pooled``). Only G0 differs: for a ``-FULL`` dataset the
observation window is the whole period, windows are 6 h (the main study's), and the
periods are the benchmark's, with no gaps. Nothing here reads a label.
"""

from __future__ import annotations

import os
import shutil
from datetime import date, datetime, timedelta
from itertools import combinations
from pathlib import Path
from typing import Any

from finmesh.data.schema import dataset_files
from finmesh.data.splits import ObservationWindow, Period, SplitPlan, daily_rows

SUFFIX = "-FULL"
WINDOW_HOURS = 6
FRACTIONS = (0.6, 0.2, 0.2)


def is_benchmark(name: str) -> bool:
    return name.endswith(SUFFIX)


def source_of(name: str) -> str:
    return name.removesuffix(SUFFIX)


def link_benchmark(raw_root: Path, source: str) -> dict[str, Any]:
    """Create ``<raw_root>/<source>-FULL/`` with the source's three files under the new
    dataset's file names."""
    name = source + SUFFIX
    src, dst = raw_root / source, raw_root / name
    a, b = dataset_files(source), dataset_files(name)
    pairs = [
        (src / a.transactions, dst / b.transactions),
        (src / a.patterns, dst / b.patterns),
        (src / a.accounts, dst / b.accounts),
    ]
    missing = [str(s) for s, _ in pairs if not s.exists()]
    if missing:
        raise FileNotFoundError(f"missing source files: {missing}")
    dst.mkdir(parents=True, exist_ok=True)
    how = "symlink"
    for s, d in pairs:
        if d.exists() or d.is_symlink():
            d.unlink()
        try:
            os.symlink(s.resolve(), d)
        except OSError:
            shutil.copyfile(s, d)
            how = "copy"
    return {"dataset": name, "source": source, "files": [str(d) for _, d in pairs], "how": how}


def day_split(rows: list[int], fractions: tuple[float, ...] = FRACTIONS) -> tuple[int, int]:
    """(i, j): train is days [0, i), validation [i, j), test [j, n). The pair minimises the
    largest relative error of the three shares against ``fractions`` (the benchmark's rule;
    ties go to the earliest pair)."""
    n = len(rows)
    total = float(sum(rows))
    prefix = [0]
    for r in rows:
        prefix.append(prefix[-1] + r)
    best: tuple[float, int, int] | None = None
    for i, j in combinations(range(1, n), 2):
        shares = (prefix[i] / total, (prefix[j] - prefix[i]) / total, 1 - prefix[j] / total)
        err = max(abs(s - t) / t for s, t in zip(shares, fractions, strict=True))
        if best is None or err < best[0]:
            best = (err, i, j)
    if best is None:
        raise ValueError(f"need at least 3 days for a 3-way day split, found {n}")
    return best[1], best[2]


def benchmark_plan(transactions: Path) -> tuple[ObservationWindow, SplitPlan, dict[str, Any]]:
    """The full-period observation window and the benchmark's day split (label-free)."""
    daily = daily_rows(transactions)
    if daily.is_empty():
        raise ValueError("no transactions")
    days: list[date] = daily["day"].to_list()
    first, last = min(days), max(days)
    all_days = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    by_day = dict(zip(days, daily["rows"].to_list(), strict=True))
    rows = [int(by_day.get(d, 0)) for d in all_days]
    i, j = day_split(rows)
    start = datetime.combine(all_days[0], datetime.min.time())
    end = datetime.combine(all_days[-1], datetime.min.time()) + timedelta(days=1)
    ordered = sorted(rows)
    n = len(ordered)
    median = float(ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2)
    observation = ObservationWindow(
        start=start,
        end=end,
        dense_days=len(all_days),
        median_daily_rows=median,
        rows_in_window=sum(rows),
        rows_before=0,
        rows_after=0,
        laundering_rows_after=0,
    )
    t_i = start + timedelta(days=i)
    t_j = start + timedelta(days=j)
    periods = (
        Period("train", start, t_i),
        Period("gap", t_i, t_i),
        Period("val", t_i, t_j),
        Period("gap", t_j, t_j),
        Period("test", t_j, end),
    )
    total = sum(rows)
    per_day = 24 // WINDOW_HOURS
    info = {
        "window_hours": WINDOW_HOURS,
        "windows": len(all_days) * per_day,
        "train": i * per_day,
        "val": (j - i) * per_day,
        "test": (len(all_days) - j) * per_day,
        "meets_rule": "benchmark split",
        "rule": "A25 P6: AMLworld benchmark day split (60/20/20, smallest largest relative "
        "error), every transaction, 6 h windows, no gaps",
        "days": len(all_days),
        "boundaries": {"val_from": str(all_days[i]), "test_from": str(all_days[j])},
        "shares": {
            "train": sum(rows[:i]) / total,
            "val": sum(rows[i:j]) / total,
            "test": sum(rows[j:]) / total,
        },
    }
    return observation, SplitPlan(WINDOW_HOURS, observation, periods), info


__all__ = [
    "SUFFIX",
    "benchmark_plan",
    "day_split",
    "is_benchmark",
    "link_benchmark",
    "source_of",
]
