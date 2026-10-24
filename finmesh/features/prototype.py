"""Week-2 timing spike for the per-bank graph feature extractor.

Not the week-4 extractor: it computes a handful of features for the largest
federation member over the first training day, so the cost of a member-day
can be measured on the real data before the full design is frozen.

Features per (member account, window), from the member's own view:
out- and in-degree, distinct counterparties out and in (fan-out, fan-in),
amounts out and in, pass-through ratio min(in, out) / max(in, out), share of
counterparties at other banks, and 2-cycles (counterparties the account both
paid and was paid by in the same window). Self-transfers carry no
counterparty, so they are counted separately and excluded from graph
features (week-1 finding 8).
"""

from __future__ import annotations

import json
import time
from datetime import timedelta
from typing import Any

import polars as pl

from finmesh.data.consortium import ConsortiumSpec, bank_sizes, build_membership
from finmesh.data.visibility import attach_members
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak


def _plan_start_and_hours(paths: DatasetPaths) -> tuple[Any, int]:
    plan = json.loads((paths.parquet / "split_plan.json").read_text())
    start = pl.Series([plan["observation"]["start"]]).str.to_datetime()[0]
    return start, int(plan["window_hours"])


def member_edges(view: pl.LazyFrame, member: int) -> pl.LazyFrame:
    """One row per (member account, counterparty, direction) leg."""
    out_legs = view.filter(pl.col("src_member") == member).select(
        pl.col("src_key").alias("account"),
        pl.col("dst_key").alias("counterparty"),
        pl.col("to_bank").alias("cp_bank"),
        pl.col("from_bank").alias("own_bank"),
        pl.col("amount_paid").alias("amount"),
        pl.lit("out").alias("dir"),
        "window",
    )
    in_legs = view.filter(pl.col("dst_member") == member).select(
        pl.col("dst_key").alias("account"),
        pl.col("src_key").alias("counterparty"),
        pl.col("from_bank").alias("cp_bank"),
        pl.col("to_bank").alias("own_bank"),
        pl.col("amount_received").alias("amount"),
        pl.lit("in").alias("dir"),
        "window",
    )
    return pl.concat([out_legs, in_legs])


def member_window_features(edges: pl.LazyFrame) -> pl.LazyFrame:
    graph = edges.filter(pl.col("account") != pl.col("counterparty"))
    out_ = pl.col("dir") == "out"
    in_ = pl.col("dir") == "in"
    feats = graph.group_by("account", "window").agg(
        out_.sum().alias("out_degree"),
        in_.sum().alias("in_degree"),
        pl.col("counterparty").filter(out_).n_unique().alias("fan_out"),
        pl.col("counterparty").filter(in_).n_unique().alias("fan_in"),
        pl.col("amount").filter(out_).sum().alias("amount_out"),
        pl.col("amount").filter(in_).sum().alias("amount_in"),
        (pl.col("cp_bank") != pl.col("own_bank")).mean().alias("cross_bank_share"),
    )
    pairs = graph.select("account", "window", "counterparty", "dir").unique()
    two_cycles = (
        pairs.filter(pl.col("dir") == "out")
        .join(
            pairs.filter(pl.col("dir") == "in"),
            on=["account", "window", "counterparty"],
            how="inner",
        )
        .group_by("account", "window")
        .agg(pl.len().alias("two_cycles"))
    )
    self_transfers = (
        edges.filter((pl.col("account") == pl.col("counterparty")) & (pl.col("dir") == "out"))
        .group_by("account", "window")
        .agg(pl.len().alias("self_transfers"))
    )
    return (
        feats.join(two_cycles, on=["account", "window"], how="left")
        .join(self_transfers, on=["account", "window"], how="full", coalesce=True)
        .with_columns(
            pl.col("two_cycles", "self_transfers", "out_degree", "in_degree").fill_null(0),
            (
                pl.min_horizontal("amount_in", "amount_out")
                / pl.max_horizontal("amount_in", "amount_out")
            )
            .fill_nan(None)
            .alias("pass_through"),
        )
    )


def time_member_day(paths: DatasetPaths, option: str | None = None) -> dict[str, Any]:
    start, hours = _plan_start_and_hours(paths)
    if option is None:
        candidates = sorted(paths.parquet.glob("membership_*.parquet"))
        if not candidates:
            raise SystemExit("run `finmesh g0` first, or pass --option")
        membership = pl.read_parquet(candidates[0])
        option = candidates[0].stem.removeprefix("membership_")
    else:
        membership = build_membership(bank_sizes(paths.transactions), ConsortiumSpec.parse(option))
    sizes = (
        bank_sizes(paths.transactions)
        .join(membership, on="bank")
        .group_by("member")
        .agg(pl.col("accounts").sum())
        .sort("accounts", descending=True)
    )
    member = int(sizes["member"][0])
    day_end = start + timedelta(days=1)
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        day = (
            pl.scan_parquet(paths.transactions)
            .filter((pl.col("timestamp") >= start) & (pl.col("timestamp") < day_end))
            .with_columns(window_index_expr_from(start, hours))
        )
        view = attach_members(day, membership).filter(
            (pl.col("src_member") == member) | (pl.col("dst_member") == member)
        )
        rows = view.select(pl.len()).collect(engine="streaming").item()
        features = member_window_features(member_edges(view, member)).collect()
    seconds = time.perf_counter() - t0
    return {
        "option": option,
        "member": member,
        "member_accounts": int(sizes["accounts"][0]),
        "day": f"{start:%Y-%m-%d}",
        "window_hours": hours,
        "visible_rows": int(rows),
        "account_windows": features.height,
        "seconds": round(seconds, 2),
        "rows_per_second": round(rows / seconds) if seconds else None,
        "peak_memory_mb": anon.mb,
        "feature_columns": [c for c in features.columns if c not in ("account", "window")],
    }


def window_index_expr_from(start: Any, hours: int) -> pl.Expr:
    seconds = (pl.col("timestamp") - pl.lit(start)).dt.total_seconds()
    return (seconds // (hours * 3600)).cast(pl.Int32).alias("window")


__all__ = ["member_edges", "member_window_features", "time_member_day", "window_index_expr_from"]
