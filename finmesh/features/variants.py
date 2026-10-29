"""Edge-table variants of the member-view build (week 11; amendment A18).

Both act on the label-free edge table before any feature is computed, so every
feature (an account's own and its neighbours') is recomputed consistently.

* :func:`degree_cap`: **each account keeps at most D distinct counterparties**
  over the observation window: the first D it transacted with, in time order
  (ties by a fixed hash). An edge survives only if each end is within the
  other's first D. An account can then appear in the graph features of at most
  D direct neighbours: its contribution to neighbour counts is clipped
  (proposal section 9.2). Self-transfers are kept.
* :func:`remove_accounts`: every transaction of the given accounts is dropped,
  for the indirect-influence measurement (features recomputed with accounts
  removed).

Each returns ``(tag, apply)``; ``apply(edges_path)`` rewrites the table in place
and returns a summary for the build's meta.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import polars as pl

EdgeFilter = Callable[[Path], dict[str, Any]]
DEFAULT_DEGREE_CAP = 16  # amendment A18
CAP_PARTS = 16  # account-hash partitions: the pair ranking never holds every pair at once


def _rewrite(edges: Path, lf: pl.LazyFrame) -> tuple[int, int]:
    before: int = pl.scan_parquet(edges).select(pl.len()).collect().item()
    tmp = edges.with_suffix(".tmp.parquet")
    lf.sink_parquet(tmp, compression="zstd")
    tmp.replace(edges)
    after: int = pl.scan_parquet(edges).select(pl.len()).collect().item()
    return before, after


def degree_cap(cap: int, parts: int = CAP_PARTS) -> tuple[str, EdgeFilter]:
    def apply(edges: Path) -> dict[str, Any]:
        work = edges.parent / f"_cap{cap}"
        work.mkdir(exist_ok=True)
        lf = pl.scan_parquet(edges)
        both = pl.concat(
            [
                lf.select(pl.col("src").alias("a"), pl.col("dst").alias("b"), "timestamp"),
                lf.select(pl.col("dst").alias("a"), pl.col("src").alias("b"), "timestamp"),
            ]
        ).filter(pl.col("a") != pl.col("b"))
        # 1. Each account's first `cap` counterparties, one hash partition of accounts at a time.
        for k in range(parts):
            (
                both.filter(pl.col("a").hash(seed=5) % parts == k)
                .group_by("a", "b")
                .agg(pl.col("timestamp").min().alias("t"))
                .collect(engine="streaming")
                .with_columns(pl.col("b").hash(seed=11).alias("h"))
                .sort("a", "t", "h")
                .with_columns(pl.int_range(pl.len()).over("a").alias("r"))
                .filter(pl.col("r") < cap)
                .select("a", "b")
                .write_parquet(work / f"allowed_{k:02d}.parquet")
            )
        # 2. Keep an edge when each end is within the other's cap: sender side, then receiver.
        cross = lf.filter(pl.col("src") != pl.col("dst"))
        for k in range(parts):
            allowed = pl.scan_parquet(work / f"allowed_{k:02d}.parquet")
            cross.filter(pl.col("src").hash(seed=5) % parts == k).join(
                allowed.rename({"a": "src", "b": "dst"}), on=["src", "dst"], how="semi"
            ).sink_parquet(work / f"by_src_{k:02d}.parquet")
        by_src = pl.scan_parquet(work / "by_src_*.parquet")
        for k in range(parts):
            allowed = pl.scan_parquet(work / f"allowed_{k:02d}.parquet")
            by_src.filter(pl.col("dst").hash(seed=5) % parts == k).join(
                allowed.rename({"a": "dst", "b": "src"}), on=["src", "dst"], how="semi"
            ).sink_parquet(work / f"kept_{k:02d}.parquet")
        kept = pl.concat(
            [lf.filter(pl.col("src") == pl.col("dst")), pl.scan_parquet(work / "kept_*.parquet")]
        )
        before, after = _rewrite(edges, kept)
        shutil.rmtree(work)
        return {"degree_cap": cap, "edges_before": before, "edges_after": after}

    return f"cap{cap}", apply


def remove_accounts(accounts: Sequence[int], tag: str) -> tuple[str, EdgeFilter]:
    gone = pl.DataFrame({"account": list(accounts)}, schema={"account": pl.UInt64})

    def apply(edges: Path) -> dict[str, Any]:
        lf = (
            pl.scan_parquet(edges)
            .join(gone.lazy(), left_on="src", right_on="account", how="anti")
            .join(gone.lazy(), left_on="dst", right_on="account", how="anti")
        )
        before, after = _rewrite(edges, lf)
        return {"removed_accounts": len(accounts), "edges_before": before, "edges_after": after}

    return tag, apply


__all__ = ["DEFAULT_DEGREE_CAP", "EdgeFilter", "degree_cap", "remove_accounts"]
