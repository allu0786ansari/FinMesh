from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest

from finmesh.data.fixture import FixtureTruth
from finmesh.data.schema import CANONICAL_COLUMNS
from finmesh.data.splits import (
    MIN_TEST_WINDOWS,
    ObservationWindow,
    assign_schemes,
    choose_window_hours,
    detect_observation_window,
    partition_expr,
    plan_split,
    scheme_transactions,
    transaction_split,
    window_activity,
    window_counts,
    window_index_expr,
)
from finmesh.paths import DatasetPaths


def _window(days: int = 10) -> ObservationWindow:
    start = datetime(2022, 9, 1)
    return ObservationWindow(
        start=start,
        end=start + timedelta(days=days),
        dense_days=days,
        median_daily_rows=1.0,
        rows_in_window=0,
        rows_before=0,
        rows_after=0,
        laundering_rows_after=0,
    )


def test_dense_window_excludes_tail(
    fixture_paths: DatasetPaths, fixture_truth: FixtureTruth, ingested: dict[str, object]
) -> None:
    ow = detect_observation_window(fixture_paths.transactions)
    assert ow.start == datetime(2022, 9, 1)
    assert ow.end == datetime(2022, 9, 11)
    assert ow.dense_days == 10
    assert ow.rows_after == fixture_truth.tail_rows
    assert ow.laundering_rows_after == fixture_truth.tail_laundering_rows
    assert ow.rows_before == 0
    assert ow.rows_in_window + ow.rows_after == fixture_truth.rows


def test_dense_window_picks_longest_run(tmp_path: pytest.TempPathFactory) -> None:
    # Two dense runs (3 days, then 5 days) separated by a quiet day.
    rows = []
    for day, n in enumerate([100, 100, 100, 1, 100, 100, 100, 100, 100, 2]):
        when = datetime(2022, 9, 1) + timedelta(days=day, hours=1)
        rows += [{"timestamp": when, "is_laundering": 0}] * n
    path = tmp_path / "t.parquet"  # type: ignore[operator]
    pl.DataFrame(rows).write_parquet(path)
    ow = detect_observation_window(path)
    assert ow.start == datetime(2022, 9, 5)
    assert ow.end == datetime(2022, 9, 10)
    assert ow.dense_days == 5


def test_window_length_rule() -> None:
    hours, table = choose_window_hours(_window(10))
    assert hours == 6
    rows = {r["window_hours"]: r for r in table}
    assert rows[12]["meets_rule"] is False  # only 4 test windows
    assert rows[6]["test"] >= MIN_TEST_WINDOWS
    hours16, _ = choose_window_hours(_window(16))
    assert hours16 == 6  # 16 days of 12 h windows give 6 test windows, still too few


def test_window_counts_add_up() -> None:
    for n in (20, 40, 60, 64):
        train, val, test = window_counts(n)
        assert train + val + test + 2 == n
        assert val == test


def test_plan_is_contiguous_and_whole_windows() -> None:
    plan = plan_split(_window(10), 6)
    names = [p.name for p in plan.periods]
    assert names == ["train", "gap", "val", "gap", "test"]
    for a, b in zip(plan.periods, plan.periods[1:], strict=False):
        assert a.end == b.start
    assert plan.periods[0].start == datetime(2022, 9, 1)
    assert plan.periods[-1].end == datetime(2022, 9, 11)
    for p in plan.periods:
        assert p.hours % 6 == 0
    assert plan.period("test").hours == 48
    assert plan.windows_in("train") == 22


def test_partition_and_window_index() -> None:
    plan = plan_split(_window(10), 6)
    ts = [
        datetime(2022, 8, 31, 23),  # before
        datetime(2022, 9, 1, 0),  # first train window
        datetime(2022, 9, 6, 13),  # gap
        datetime(2022, 9, 7, 0),  # val
        datetime(2022, 9, 10, 23, 59),  # last test window
        datetime(2022, 9, 11, 0),  # tail
    ]
    out = pl.DataFrame({"timestamp": ts}).select(
        partition_expr(plan).cast(pl.String).alias("p"), window_index_expr(plan).alias("w")
    )
    assert out["p"].to_list() == ["outside", "train", "gap", "val", "test", "outside"]
    assert out["w"].to_list() == [None, 0, 22, 24, 39, None]


def test_scheme_assignment_and_masking(
    fixture_paths: DatasetPaths, fixture_truth: FixtureTruth, ingested: dict[str, object]
) -> None:
    ow = detect_observation_window(fixture_paths.transactions)
    plan = plan_split(ow, 6)
    schemes = pl.read_parquet(fixture_paths.schemes)
    stx = scheme_transactions(fixture_paths.transactions, fixture_paths.scheme_links, plan)
    assignment = assign_schemes(stx, schemes, plan)
    assert assignment.height == fixture_truth.schemes
    assert int(assignment["truncated"].sum()) == fixture_truth.truncated_schemes
    # Every scheme's assigned partition is the partition of its first in-window row.
    first = (
        stx.filter(pl.col("tx_partition") != "outside")
        .group_by("scheme_id")
        .agg(pl.col("tx_partition").sort_by("timestamp").first().alias("expected"))
    )
    check = assignment.join(first, on="scheme_id")
    assert (check["partition"] == check["expected"]).all()

    split = transaction_split(
        fixture_paths.transactions, fixture_paths.scheme_links, assignment, plan
    ).collect()
    assert split.height == fixture_truth.rows
    # Masked: everything in gaps or outside, plus scheme rows outside their own partition.
    joined = split.join(
        assignment.select("scheme_id", pl.col("partition").alias("sp")), on="scheme_id", how="left"
    )
    expected_mask = (
        (pl.col("partition") == "gap")
        | (pl.col("partition") == "outside")
        | (pl.col("scheme_id").is_not_null() & (pl.col("sp") != pl.col("partition")))
    )
    assert joined.select((pl.col("eval_mask") == expected_mask).all()).item()
    # Unmasked scheme rows are exactly the rows in their scheme's own partition.
    own = int(assignment["rows_in_partition"].sum())
    unmasked_scheme_rows = split.filter(
        pl.col("scheme_id").is_not_null() & ~pl.col("eval_mask")
    ).height
    gap_scheme_rows = int(
        assignment.filter(pl.col("partition") == "gap")["rows_in_partition"].sum()
    )
    assert unmasked_scheme_rows == own - gap_scheme_rows


def test_window_activity_is_label_free(
    fixture_paths: DatasetPaths, ingested: dict[str, object]
) -> None:
    ow = detect_observation_window(fixture_paths.transactions)
    rows = window_activity(fixture_paths.transactions, ow, sample_mod=1)
    assert [r["window_hours"] for r in rows] == [4, 6, 12]
    # Longer windows hold fewer, busier account-windows.
    assert rows[0]["active_account_windows"] >= rows[2]["active_account_windows"]
    assert set(CANONICAL_COLUMNS) >= {"is_laundering"}  # the function never selects it
