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


def test_link_edges_touching_equals_filtering_the_full_table(
    fixture_paths: object, ingested: dict[str, object]
) -> None:
    from finmesh.data.consortium import ConsortiumSpec, bank_sizes, build_membership
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.split_io import load_plan
    from finmesh.fusion.local import link_edges
    from finmesh.paths import DatasetPaths

    assert isinstance(fixture_paths, DatasetPaths)
    run_g0(fixture_paths)
    plan = load_plan(fixture_paths)
    membership = build_membership(
        bank_sizes(fixture_paths.transactions), ConsortiumSpec.parse("B8")
    )
    full = link_edges(fixture_paths.transactions, plan, 20, 30, 12, membership)
    some = full.select(pl.col("src").alias("account")).unique().head(25)
    cut = link_edges(fixture_paths.transactions, plan, 20, 30, 12, membership, touching=some)
    want = full.filter(
        pl.col("src").is_in(some["account"].implode())
        | pl.col("dst").is_in(some["account"].implode())
    )
    order = ["src", "dst", "window"]
    assert cut.sort(order).equals(want.sort(order).select(cut.columns))
