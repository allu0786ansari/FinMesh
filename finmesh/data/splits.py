"""Observation window, window length and time-based splits (proposal Section 9).

Three decisions are made here, each by a rule fixed before any model exists and
none of them reading labels:

1. **Observation window.** AMLworld has a dense simulation period followed by a
   sparse tail in which licit traffic has stopped and most remaining rows are
   laundering (week-1 finding 1). The window is the longest run of
   consecutive days whose row count is at least ``DENSE_DAY_MIN_SHARE`` of the
   median daily count. Everything outside it is excluded from modelling and
   evaluation.
2. **Window length.** The largest candidate in ``WINDOW_HOURS_CANDIDATES`` for
   which the test period holds at least ``MIN_TEST_WINDOWS`` windows, so that
   per-bank alert budgets and time-to-detect are estimated on enough windows.
3. **Splits.** Train, validation and test cover consecutive whole windows in
   time order, in proportions ``SPLIT_FRACTIONS``, separated by one-window gaps.

Scheme assignment (also Section 9): a scheme belongs to the partition in which
its first in-window transaction falls. Its transactions that land in another
partition are *masked* there: they stay in the traffic that features see, but
they are neither positives nor negatives in that partition's evaluation.
Schemes that start in a gap belong to no partition.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

DENSE_DAY_MIN_SHARE = 0.05
WINDOW_HOURS_CANDIDATES: tuple[int, ...] = (4, 6, 12)
MIN_TEST_WINDOWS = 8
SPLIT_FRACTIONS: tuple[float, float, float] = (0.6, 0.2, 0.2)
GAP_WINDOWS = 1

PARTITIONS: tuple[str, ...] = ("train", "val", "test", "gap", "outside")
PartitionEnum = pl.Enum(list(PARTITIONS))


@dataclass(frozen=True)
class ObservationWindow:
    start: datetime
    end: datetime  # exclusive
    dense_days: int
    median_daily_rows: float
    rows_in_window: int
    rows_before: int
    rows_after: int
    laundering_rows_after: int

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["start"] = self.start.isoformat(sep=" ")
        d["end"] = self.end.isoformat(sep=" ")
        d["rule"] = (
            f"longest run of consecutive days with rows >= {DENSE_DAY_MIN_SHARE:.0%} "
            "of the median daily count"
        )
        return d


def daily_rows(transactions: Path) -> pl.DataFrame:
    """Rows per calendar day. Label-free by construction."""
    return (
        pl.scan_parquet(transactions)
        .group_by(pl.col("timestamp").dt.date().alias("day"))
        .agg(pl.len().alias("rows"))
        .sort("day")
        .collect(engine="streaming")
    )


def detect_observation_window(transactions: Path) -> ObservationWindow:
    daily = daily_rows(transactions)
    if daily.is_empty():
        raise ValueError("no transactions")
    median_value = daily["rows"].median()
    median = float(median_value) if isinstance(median_value, int | float) else 0.0
    dense = (daily["rows"] >= DENSE_DAY_MIN_SHARE * median).to_list()
    days = daily["day"].to_list()

    best: tuple[int, int] = (0, -1)  # (start index, end index inclusive)
    i = 0
    while i < len(days):
        if not dense[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(days) and dense[j + 1] and days[j + 1] - days[j] == timedelta(days=1):
            j += 1
        if j - i > best[1] - best[0]:
            best = (i, j)
        i = j + 1
    start = datetime.combine(days[best[0]], datetime.min.time())
    end = datetime.combine(days[best[1]], datetime.min.time()) + timedelta(days=1)

    lf = pl.scan_parquet(transactions)
    counts = (
        lf.select(
            (pl.col("timestamp") < start).sum().alias("before"),
            (pl.col("timestamp") >= end).sum().alias("after"),
            ((pl.col("timestamp") >= end) & (pl.col("is_laundering") == 1))
            .sum()
            .alias("laundering_after"),
            pl.len().alias("total"),
        )
        .collect(engine="streaming")
        .row(0, named=True)
    )
    return ObservationWindow(
        start=start,
        end=end,
        dense_days=best[1] - best[0] + 1,
        median_daily_rows=median,
        rows_in_window=int(counts["total"] - counts["before"] - counts["after"]),
        rows_before=int(counts["before"]),
        rows_after=int(counts["after"]),
        laundering_rows_after=int(counts["laundering_after"]),
    )


@dataclass(frozen=True)
class Period:
    name: str
    start: datetime
    end: datetime  # exclusive

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start": self.start.isoformat(sep=" "),
            "end": self.end.isoformat(sep=" "),
            "hours": self.hours,
        }


@dataclass(frozen=True)
class SplitPlan:
    window_hours: int
    observation: ObservationWindow
    periods: tuple[Period, ...]  # train, gap, val, gap, test in time order

    def period(self, name: str) -> Period:
        for p in self.periods:
            if p.name == name:
                return p
        raise KeyError(name)

    @property
    def n_windows(self) -> int:
        return int(self.observation.hours // self.window_hours)

    def windows_in(self, name: str) -> int:
        return int(self.period(name).hours // self.window_hours)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_hours": self.window_hours,
            "n_windows": self.n_windows,
            "fractions": SPLIT_FRACTIONS,
            "gap_windows": GAP_WINDOWS,
            "observation": self.observation.to_dict(),
            "periods": [p.to_dict() for p in self.periods],
            "windows": {n: self.windows_in(n) for n in ("train", "val", "test")},
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")


def window_counts(n_windows: int) -> tuple[int, int, int]:
    """Whole windows for (train, val, test) after removing the two gaps."""
    usable = n_windows - 2 * GAP_WINDOWS
    n_val = round(SPLIT_FRACTIONS[1] * usable)
    n_test = round(SPLIT_FRACTIONS[2] * usable)
    return usable - n_val - n_test, n_val, n_test


def choose_window_hours(observation: ObservationWindow) -> tuple[int, list[dict[str, Any]]]:
    """Largest candidate whose test period holds at least MIN_TEST_WINDOWS windows."""
    table = []
    chosen: int | None = None
    for hours in WINDOW_HOURS_CANDIDATES:
        n = int(observation.hours // hours)
        train, val, test = window_counts(n)
        ok = test >= MIN_TEST_WINDOWS and train > 0
        table.append(
            {
                "window_hours": hours,
                "windows": n,
                "train": train,
                "val": val,
                "test": test,
                "meets_rule": ok,
            }
        )
        if ok:
            chosen = hours  # candidates ascend, so the last passing one is the largest
    if chosen is None:
        chosen = WINDOW_HOURS_CANDIDATES[0]
    return chosen, table


def plan_split(observation: ObservationWindow, window_hours: int) -> SplitPlan:
    n = int(observation.hours // window_hours)
    n_train, n_val, n_test = window_counts(n)
    step = timedelta(hours=window_hours)
    t = observation.start
    periods = []
    for name, count in (
        ("train", n_train),
        ("gap", GAP_WINDOWS),
        ("val", n_val),
        ("gap", GAP_WINDOWS),
        ("test", n_test),
    ):
        periods.append(Period(name=name, start=t, end=t + count * step))
        t = t + count * step
    return SplitPlan(window_hours=window_hours, observation=observation, periods=tuple(periods))


def partition_expr(plan: SplitPlan, column: str = "timestamp") -> pl.Expr:
    """Partition label for a timestamp column, as the ``PartitionEnum`` dtype."""
    ts = pl.col(column)
    first, *rest = plan.periods
    expr: Any = pl.when((ts >= first.start) & (ts < first.end)).then(pl.lit(first.name))
    for p in rest:
        expr = expr.when((ts >= p.start) & (ts < p.end)).then(pl.lit(p.name))
    result: pl.Expr = expr.otherwise(pl.lit("outside")).cast(PartitionEnum)
    return result


def window_index_expr(plan: SplitPlan, column: str = "timestamp") -> pl.Expr:
    """Zero-based window number since the observation start (null outside)."""
    start = plan.observation.start
    seconds = (pl.col(column) - pl.lit(start)).dt.total_seconds()
    idx = (seconds // (plan.window_hours * 3600)).cast(pl.Int32)
    inside = (pl.col(column) >= start) & (pl.col(column) < plan.observation.end)
    return pl.when(inside).then(idx).otherwise(None)


def scheme_transactions(
    transactions: Path, scheme_links: Path, plan: SplitPlan, columns: tuple[str, ...] = ()
) -> pl.DataFrame:
    """Every scheme transaction with its own partition; small (thousands of rows)."""
    links = pl.read_parquet(scheme_links)
    if links["tx_id"].n_unique() != links.height:
        raise ValueError("a transaction belongs to several schemes; assignment is ambiguous")
    cols = ("tx_id", "timestamp", "src_key", "dst_key", "from_bank", "to_bank", *columns)
    return (
        pl.scan_parquet(transactions)
        .select(*dict.fromkeys(cols))
        .join(links.lazy(), on="tx_id", how="inner")
        .with_columns(partition_expr(plan).alias("tx_partition"))
        .collect(engine="streaming")
    )


def assign_schemes(scheme_tx: pl.DataFrame, schemes: pl.DataFrame, plan: SplitPlan) -> pl.DataFrame:
    """One row per scheme: assigned partition, truncation and size in each part."""
    end = plan.observation.end
    in_window = pl.col("tx_partition") != "outside"
    per = scheme_tx.group_by("scheme_id").agg(
        pl.col("timestamp").filter(in_window).min().alias("first_in_window"),
        pl.len().alias("rows_total"),
        in_window.sum().alias("rows_in_window"),
        (pl.col("timestamp") >= end).sum().alias("rows_after_window"),
    )
    assigned = per.with_columns(
        pl.when(pl.col("first_in_window").is_null())
        .then(pl.lit("outside"))
        .otherwise(partition_expr(plan, "first_in_window").cast(pl.String))
        .cast(PartitionEnum)
        .alias("partition"),
        (pl.col("rows_after_window") > 0).alias("truncated"),
    )
    own = (
        scheme_tx.join(assigned.select("scheme_id", "partition"), on="scheme_id")
        .filter(pl.col("tx_partition") == pl.col("partition"))
        .group_by("scheme_id")
        .agg(pl.len().alias("rows_in_partition"))
    )
    return (
        schemes.select("scheme_id", "pattern")
        .join(assigned, on="scheme_id", how="left")
        .join(own, on="scheme_id", how="left")
        .with_columns(pl.col("rows_in_partition").fill_null(0))
        .sort("scheme_id")
    )


def transaction_split(
    transactions: Path, scheme_links: Path, scheme_assignment: pl.DataFrame, plan: SplitPlan
) -> pl.LazyFrame:
    """Per-transaction partition and evaluation mask (lazy; written to Parquet by callers).

    ``eval_mask`` is True when a row must not count as a positive or negative
    in its partition's evaluation: it lies in a gap or outside the window, or
    it belongs to a scheme assigned to a different partition.
    """
    links = pl.scan_parquet(scheme_links).join(
        scheme_assignment.lazy().select("scheme_id", pl.col("partition").alias("scheme_partition")),
        on="scheme_id",
        how="left",
    )
    return (
        pl.scan_parquet(transactions)
        .select("tx_id", "timestamp")
        .with_columns(
            partition_expr(plan).alias("partition"),
            window_index_expr(plan).alias("window"),
        )
        .join(links, on="tx_id", how="left")
        .with_columns(
            (
                (pl.col("partition") == "gap")
                | (pl.col("partition") == "outside")
                | (
                    pl.col("scheme_id").is_not_null()
                    & (pl.col("scheme_partition") != pl.col("partition"))
                )
            ).alias("eval_mask")
        )
        .select("tx_id", "partition", "window", "scheme_id", "eval_mask")
    )


def window_activity(
    transactions: Path, observation: ObservationWindow, sample_mod: int = 10
) -> list[dict[str, Any]]:
    """How busy account-windows are for each candidate length (label-free).

    Computed on a deterministic 1-in-``sample_mod`` sample of accounts, chosen
    by a hash of the account key, so it stays cheap on the Medium sets.
    """
    lf = pl.scan_parquet(transactions).filter(
        (pl.col("timestamp") >= observation.start) & (pl.col("timestamp") < observation.end)
    )
    sides = pl.concat(
        [
            lf.select(pl.col("src_key").hash(seed=0).alias("key"), "timestamp"),
            lf.select(pl.col("dst_key").hash(seed=0).alias("key"), "timestamp"),
        ]
    ).filter(pl.col("key") % sample_mod == 0)
    out = []
    for hours in WINDOW_HOURS_CANDIDATES:
        seconds = (pl.col("timestamp") - pl.lit(observation.start)).dt.total_seconds()
        per = (
            sides.with_columns((seconds // (hours * 3600)).alias("w"))
            .group_by("key", "w")
            .agg(pl.len().alias("tx"))
        )
        stats = per.select(
            pl.len().alias("active_account_windows"),
            pl.col("tx").median().alias("median_tx_per_active_window"),
            pl.col("tx").quantile(0.9).alias("p90_tx_per_active_window"),
        ).collect(engine="streaming")
        windows_per_account = (
            per.group_by("key")
            .agg(pl.len().alias("n"))
            .select(pl.col("n").median())
            .collect(engine="streaming")
            .item()
        )
        row = stats.row(0, named=True)
        row["window_hours"] = hours
        row["median_active_windows_per_account"] = windows_per_account
        row["sample"] = f"1 in {sample_mod} accounts"
        out.append(row)
    return out
