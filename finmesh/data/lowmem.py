"""Bounded-memory counting of distinct accounts.

Counting distinct account keys per group (per bank, per member) is the most
memory-hungry query in the data layer: polars' streaming engine keeps a large
hash table per thread, and on 32 M rows a plain ``unique()`` or
``n_unique()`` inside ``group_by`` reaches 2.6–3.7 GB. WSL2 gets only half
of a Windows machine's RAM by default, so that is too close to the limit on
an 8 GB laptop.

The helpers here split the key space into slices by hash (``key % slices``)
and run the distinct count once per slice. Because a key always falls in the
same slice, per-slice counts add up exactly. Peak memory drops to about 0.6 GB
at 32 M rows, for roughly twice the run time.
"""

from __future__ import annotations

import polars as pl

KEYS_PER_SLICE = 4_000_000  # rows of (group, key) pairs per slice, before de-duplication


def slices_for(rows: int) -> int:
    return max(1, -(-rows // KEYS_PER_SLICE))


def hashed_key(column: str) -> pl.Expr:
    """64-bit hash of an account key; collisions are negligible at AMLworld scale."""
    return pl.col(column).hash(seed=0)


def distinct_keys_per_group(
    pairs: pl.LazyFrame, group: str, key: str = "key", rows: int | None = None, out: str = "n"
) -> pl.DataFrame:
    """Number of distinct ``key`` values per ``group``; ``key`` must be an integer hash."""
    n_slices = slices_for(rows if rows is not None else KEYS_PER_SLICE)
    parts = [
        pairs.filter(pl.col(key) % n_slices == i)
        .unique()
        .group_by(group)
        .agg(pl.len().alias(out))
        .collect(engine="streaming")
        for i in range(n_slices)
    ]
    return pl.concat(parts).group_by(group).agg(pl.col(out).sum())
