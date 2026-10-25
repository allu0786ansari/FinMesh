"""Week 5: local (S0) and pooled incidents on a hand-built case."""

from __future__ import annotations

import polars as pl

from finmesh.fusion.local import incidents

KEY_SCHEMA = {"member": pl.Int32, "account": pl.UInt64, "window": pl.Int32}
EDGE_SCHEMA = {"src": pl.UInt64, "dst": pl.UInt64, "window": pl.Int32}


def _groups(inc: pl.DataFrame) -> set[frozenset[tuple[int, int]]]:
    out: dict[int, set[tuple[int, int]]] = {}
    for _m, a, w, i in inc.iter_rows():
        out.setdefault(i, set()).add((a, w))
    return {frozenset(v) for v in out.values()}


def test_local_links_own_accounts_and_pooled_links_across_members() -> None:
    alerts = pl.DataFrame(
        [(0, 1, 5), (0, 2, 6), (1, 3, 6), (0, 4, 5), (0, 1, 30), (0, 5, 15), (0, 6, 15), (0, 7, 8)],
        schema=KEY_SCHEMA,
        orient="row",
    )
    edges = pl.DataFrame(
        [(1, 2, 5), (2, 3, 5), (5, 6, 0), (7, 1, 8), (4, 1, 9)],
        schema=EDGE_SCHEMA,
        orient="row",
    )
    local = _groups(incidents(alerts, edges, lookback=12, cross_member=False))
    assert frozenset({(1, 5), (2, 6), (7, 8)}) in local  # same member, recent edges
    assert frozenset({(3, 6)}) in local  # account 3 is at another member: not linkable at S0
    assert frozenset({(1, 30)}) in local  # 25 windows later: a new case
    assert frozenset({(5, 15)}) in local and frozenset({(6, 15)}) in local  # edge too old
    assert frozenset({(4, 5)}) in local  # its only edge comes after both alerts

    pooled = _groups(incidents(alerts, edges, lookback=12, cross_member=True))
    assert frozenset({(1, 5), (2, 6), (3, 6), (7, 8)}) in pooled


def test_same_account_alerts_within_lookback_are_one_case() -> None:
    alerts = pl.DataFrame([(0, 1, 5), (0, 1, 10), (0, 2, 16)], schema=KEY_SCHEMA, orient="row")
    edges = pl.DataFrame([(1, 2, 14)], schema=EDGE_SCHEMA, orient="row")
    groups = _groups(incidents(alerts, edges, lookback=12, cross_member=False))
    assert groups == {frozenset({(1, 5), (1, 10), (2, 16)})}


def test_no_alerts_gives_no_incidents() -> None:
    empty = pl.DataFrame(schema=KEY_SCHEMA)
    edges = pl.DataFrame(schema=EDGE_SCHEMA)
    assert incidents(empty, edges, 12, False).height == 0
