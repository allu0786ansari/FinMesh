"""Week-2 regression checks on the real AMLworld data (skipped when absent).

Anchors are the values measured on 24 Oct 2026 (docs/runlog/week-01.md). Run:

    uv run pytest -m real_data -v
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from finmesh.eval.g0 import is_current
from finmesh.paths import artifacts_dir, dataset_paths

# rows, laundering rows, accounts, duplicate extra rows, schemes, tail rows, tail laundering,
# dense days. Small sets measured 24 Oct, Medium sets 25 Oct 2026.
ANCHORS = {
    "HI-Small": (5_078_345, 5_177, 515_088, 9, 370, 1_108, 655, 10),
    "LI-Small": (6_924_049, 3_565, 705_907, 8, 117, 223, 134, 10),
    "HI-Medium": (31_898_238, 35_230, 2_077_023, 20, 2_756, 6_987, 4_084, 16),
    "LI-Medium": (31_251_483, 16_041, 2_032_095, 14, 456, 1_370, 771, 16),
}


@pytest.mark.real_data
@pytest.mark.parametrize("name", sorted(ANCHORS))
def test_ingest_counts_are_exact(name: str) -> None:
    """Hash-based duplicate and account counts (week 2) equal the week-1 exact counts."""
    paths = dataset_paths(name)
    if not paths.ingest_report.exists():
        pytest.skip(f"{name} not ingested")
    tx = json.loads(paths.ingest_report.read_text())["result"]["transactions"]
    rows, laundering, accounts, dups, *_ = ANCHORS[name]
    assert (tx["rows"], tx["laundering_rows"], tx["accounts"]) == (rows, laundering, accounts)
    assert tx["duplicate_extra_rows"] == dups


@pytest.mark.real_data
@pytest.mark.parametrize("name", sorted(ANCHORS))
def test_g0_window_and_split(name: str) -> None:
    path = artifacts_dir() / "week02" / f"g0_{name}.json"
    if not path.exists():
        pytest.skip(f"G0 not run for {name}")
    result = json.loads(path.read_text())["result"]
    if not is_current(result):
        pytest.skip(
            f"G0 result for {name} predates amendment A5; run `finmesh g0 --dataset {name}`"
        )
    *_, schemes, tail_rows, tail_laundering, days = ANCHORS[name]
    ow = result["observation_window"]
    assert ow["start"] == str(datetime(2022, 9, 1))
    assert ow["end"] == str(datetime(2022, 9, 1 + days))
    assert ow["rows_after"] == tail_rows
    assert ow["laundering_rows_after"] == tail_laundering
    assert result["window_hours"] == 6
    assert result["schemes_total"] == schemes
    assert result["test"]["option"] == result["selection"]["option"] == "B8"  # amendment A5
