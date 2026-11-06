"""A25 P1: a fixed-length window of a Large AMLworld set, as a dataset of its own.

HI-Large and LI-Large cover 97 days (about 180 M transactions each). The rule, fixed in
`docs/protocol/improvement_plan_A25.md` before any Large file was read:

1. find the dense period with the A1 rule (longest run of consecutive days with at least
   5% of the median daily row count; :func:`finmesh.data.splits.longest_dense_run`);
2. keep the **16 consecutive calendar days ending at the end of the dense period**.

The cut works on the raw files, line by line, in bounded memory: transactions whose day is
in the window; pattern blocks restricted to their lines in the window (a block with none
left is dropped); the accounts file unchanged. The result is written as raw files of a new
dataset ``<source>-W<days>`` (for example ``HI-Large-W16``), which then goes through the
same pipeline as every other dataset (`finmesh week1`, `g0`, `labels`, `features`, ...).
Reading counts per day uses no label.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from finmesh.data.schema import dataset_files
from finmesh.data.splits import longest_dense_run

WINDOW_DAYS = 16


def _day(line: bytes) -> date | None:
    try:
        return datetime.strptime(line[:10].decode("ascii"), "%Y/%m/%d").date()
    except (UnicodeDecodeError, ValueError):
        return None


def daily_counts(trans_csv: Path) -> dict[date, int]:
    """Rows per calendar day of a raw transactions file (first pass; label-free)."""
    counts: Counter[bytes] = Counter()
    with trans_csv.open("rb") as f:
        next(f, None)  # header
        for line in f:
            counts[line[:10]] += 1
    out: dict[date, int] = {}
    for key, n in counts.items():
        d = _day(key)
        if d is not None:
            out[d] = out.get(d, 0) + n
    return dict(sorted(out.items()))


def choose_window(daily: dict[date, int], days: int = WINDOW_DAYS) -> tuple[date, date]:
    """(first day, last day) of the ``days`` days ending at the end of the dense period."""
    all_days = list(daily)
    i, j = longest_dense_run(all_days, list(daily.values()))
    dense_len = j - i + 1
    if dense_len < days:
        raise ValueError(f"the dense period has {dense_len} days, fewer than {days}")
    last = all_days[j]
    return last - timedelta(days=days - 1), last


def cut_window(raw_root: Path, source: str, days: int = WINDOW_DAYS) -> dict[str, Any]:
    """Write ``<raw_root>/<source>-W<days>/`` from ``<raw_root>/<source>/``."""
    src = raw_root / source
    name = f"{source}-W{days}"
    dst = raw_root / name
    files, out_files = dataset_files(source), dataset_files(name)
    trans = src / files.transactions
    if not trans.exists():
        raise FileNotFoundError(f"{trans} not found; download {source} from Kaggle first")
    daily = daily_counts(trans)
    first, last = choose_window(daily, days)
    keep = {(first + timedelta(days=k)).strftime("%Y/%m/%d").encode() for k in range(days)}
    dst.mkdir(parents=True, exist_ok=True)

    kept = 0
    with trans.open("rb") as f, (dst / out_files.transactions).open("wb") as out:
        out.write(next(f))
        for line in f:
            if line[:10] in keep:
                out.write(line)
                kept += 1

    blocks_in = blocks_out = lines_out = 0
    patterns = src / files.patterns
    if patterns.exists():
        with patterns.open("rb") as f, (dst / out_files.patterns).open("wb") as out:
            block: list[bytes] = []
            header: bytes | None = None
            for line in f:
                if line.startswith(b"BEGIN"):
                    header, block = line, []
                    blocks_in += 1
                elif line.startswith(b"END"):
                    if header is not None and block:
                        out.write(header)
                        out.writelines(block)
                        out.write(line)
                        out.write(b"\n")
                        blocks_out += 1
                        lines_out += len(block)
                    header, block = None, []
                elif header is not None and line[:10] in keep:
                    block.append(line)
    accounts = src / files.accounts
    if accounts.exists():
        shutil.copyfile(accounts, dst / out_files.accounts)

    dense_i, dense_j = longest_dense_run(list(daily), list(daily.values()))
    report = {
        "source": source,
        "dataset": name,
        "rule": f"{days} consecutive days ending at the end of the dense period (A1 rule)",
        "source_days": len(daily),
        "dense_period": [str(list(daily)[dense_i]), str(list(daily)[dense_j])],
        "window": [str(first), str(last)],
        "transactions": kept,
        "pattern_blocks": {"source": blocks_in, "kept": blocks_out, "lines": lines_out},
    }
    (dst / "window.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


__all__ = ["WINDOW_DAYS", "choose_window", "cut_window", "daily_counts"]
