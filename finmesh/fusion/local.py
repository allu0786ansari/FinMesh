"""Incidents without sharing: link alerts that transacted with each other.

An incident is a set of alerted account-windows that an analyst would open as
one case. Without evidence sharing (S0), a bank can only link its **own**
alerted accounts: two alerted account-windows at the same member are linked
when the accounts transacted directly (either direction) within the lookback
ending at the later of the two windows, and the windows are less than a
lookback apart. The same account's alerts within a lookback are one case.
Incidents are the connected components of these links.

The pooled oracle applies the same rule with every member's alerts visible
to every other (``cross_member=True``). Week 7 replaces this with the fusion
layer for the sharing levels S1–S4; S0 and the oracle keep this rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from finmesh.data.lowmem import hashed_key
from finmesh.data.splits import SplitPlan, window_index_expr

KEYS = ("member", "account", "window")


def link_edges(
    transactions: Path, plan: SplitPlan, first: int, last: int, lookback: int
) -> pl.DataFrame:
    """Distinct (src, dst, window) pairs in windows first - lookback + 1 .. last, no self-loops."""
    w = window_index_expr(plan).alias("window")
    return (
        pl.scan_parquet(transactions)
        .select(hashed_key("src_key").alias("src"), hashed_key("dst_key").alias("dst"), w)
        .filter(
            pl.col("window").is_between(first - lookback + 1, last)
            & (pl.col("src") != pl.col("dst"))
        )
        .unique()
        .collect(engine="streaming")
    )


@dataclass(frozen=True)
class Linker:
    """Builds incidents from alerts; ``name`` identifies the rule in reports."""

    edges: pl.DataFrame
    lookback: int
    cross_member: bool

    @property
    def name(self) -> str:
        return "pooled" if self.cross_member else "local"

    def __call__(self, alerts: pl.DataFrame) -> pl.DataFrame:
        return incidents(alerts, self.edges, self.lookback, self.cross_member)


def incidents(
    alerts: pl.DataFrame, edges: pl.DataFrame, lookback: int, cross_member: bool
) -> pl.DataFrame:
    """``alerts``: alerted rows with member, account, window. Returns KEYS + incident."""
    nodes = alerts.select(KEYS).unique().sort(KEYS).with_row_index("node")
    if nodes.height == 0:
        return nodes.select(*KEYS, pl.lit(0, pl.UInt32).alias("incident"))
    accts = nodes.select("account").unique()
    near = edges.join(accts, left_on="src", right_on="account", how="semi").join(
        accts, left_on="dst", right_on="account", how="semi"
    )
    a = nodes.rename({"account": "src", "window": "wa", "member": "ma", "node": "na"})
    b = nodes.rename({"account": "dst", "window": "wb", "member": "mb", "node": "nb"})
    later = pl.max_horizontal("wa", "wb")
    pairs = (
        near.join(a, on="src")
        .join(b, on="dst")
        .filter(
            (pl.col("window") <= later)
            & (pl.col("window") > later - lookback)
            & ((pl.col("wa") - pl.col("wb")).abs() < lookback)
        )
    )
    if not cross_member:
        pairs = pairs.filter(pl.col("ma") == pl.col("mb"))
    same = (
        nodes.join(nodes, on="account", suffix="_b")
        .filter(
            (pl.col("node") < pl.col("node_b"))
            & ((pl.col("window") - pl.col("window_b")).abs() < lookback)
        )
        .select(pl.col("node").alias("na"), pl.col("node_b").alias("nb"))
    )
    links = pl.concat([pairs.select("na", "nb"), same])
    n = nodes.height
    graph = coo_matrix(
        (np.ones(links.height), (links["na"].to_numpy(), links["nb"].to_numpy())), shape=(n, n)
    )
    _, component = connected_components(graph, directed=False)
    return nodes.with_columns(pl.Series("incident", component.astype(np.uint32))).select(
        *KEYS, "incident"
    )
