"""Checks on the real AMLworld files. Skipped unless they have been ingested.

Run on your machine after `finmesh week1 --dataset HI-Small`:

    uv run pytest -m real_data -v

The expected values come from published descriptions of the datasets
(Altman et al., NeurIPS 2023; reviews that report HI-Small graph sizes). They
are deliberately loose: the point is to catch a wrong file or a broken
loader, not to re-derive the paper.
"""

from __future__ import annotations

import json

import polars as pl
import pytest

from finmesh.paths import dataset_paths

EXPECTED = {
    # dataset: (approx rows, approx 1-in-N laundering rate)
    "HI-Small": (5_078_345, 981),
    "LI-Small": (6_900_000, 1_942),  # "about 7 M" in the proposal; refine at G0
}


@pytest.mark.real_data
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_real_dataset_matches_published_size(name: str) -> None:
    paths = dataset_paths(name)
    if not paths.ingest_report.exists():
        pytest.skip(f"{name} not ingested under {paths.root}")
    report = json.loads(paths.ingest_report.read_text())["result"]
    tx = report["transactions"]
    rows, one_in = EXPECTED[name]
    assert abs(tx["rows"] - rows) / rows < 0.02, tx["rows"]
    observed_one_in = tx["rows"] / max(tx["laundering_rows"], 1)
    assert 0.85 * one_in < observed_one_in < 1.15 * one_in, observed_one_in
    assert tx["malformed_cells"] == 0


@pytest.mark.real_data
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_real_patterns_link(name: str) -> None:
    paths = dataset_paths(name)
    if not paths.scheme_links.exists():
        pytest.skip(f"{name} pattern links not built")
    report = json.loads(paths.ingest_report.read_text())["result"]["linking"]
    # Nearly every pattern line must find its transaction row.
    assert report["unmatched_pattern_rows"] <= 0.01 * report["pattern_rows"], report
    schemes = pl.read_parquet(paths.schemes)
    assert schemes.height > 100
    assert set(schemes["pattern"].unique()) <= {
        "FAN-OUT",
        "FAN-IN",
        "GATHER-SCATTER",
        "SCATTER-GATHER",
        "CYCLE",
        "RANDOM",
        "BIPARTITE",
        "STACK",
    }
