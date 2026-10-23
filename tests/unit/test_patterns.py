from __future__ import annotations

from pathlib import Path

import polars as pl

from finmesh.data.fixture import FixtureTruth
from finmesh.data.patterns import parse_pattern_file, summarise_schemes
from finmesh.data.schema import dataset_files
from finmesh.paths import DatasetPaths


def test_parse_counts_match_truth(fixture_paths: DatasetPaths, fixture_truth: FixtureTruth) -> None:
    rows, report = parse_pattern_file(
        fixture_paths.raw / dataset_files(fixture_paths.name).patterns
    )
    assert report.schemes == fixture_truth.schemes
    assert report.pattern_rows == fixture_truth.pattern_rows
    assert report.malformed_rows == 0
    assert report.unclosed_blocks == 0
    counts = dict(
        rows.group_by("scheme_id")
        .agg(pl.col("pattern").first())
        .group_by("pattern")
        .len()
        .iter_rows()
    )
    assert counts == fixture_truth.schemes_by_pattern


def test_multi_bank_schemes(fixture_paths: DatasetPaths, fixture_truth: FixtureTruth) -> None:
    rows, _ = parse_pattern_file(fixture_paths.raw / dataset_files(fixture_paths.name).patterns)
    summary = summarise_schemes(rows)
    assert int((summary["n_banks"] >= 2).sum()) == fixture_truth.multi_bank_schemes
    assert fixture_truth.multi_bank_schemes < fixture_truth.schemes  # some stay in one bank


def test_linking_is_exact(ingested: dict[str, object], fixture_truth: FixtureTruth) -> None:
    link = ingested["linking"]
    assert isinstance(link, dict)
    assert link["pattern_rows"] == fixture_truth.pattern_rows
    assert link["unmatched_pattern_rows"] == 0
    assert link["ambiguous_pattern_rows"] == 0
    assert link["linked_transactions"] == fixture_truth.pattern_rows
    assert link["linked_rows_labelled_licit"] == 0
    assert link["schemes_with_no_linked_rows"] == 0


def test_parser_tolerates_damage(tmp_path: Path) -> None:
    text = "\n".join(
        [
            "2022/09/01 00:00,1,A,2,B,1.00,US Dollar,1.00,US Dollar,ACH,1",  # outside any block
            "BEGIN LAUNDERING ATTEMPT - ZIGZAG",  # unknown pattern name
            "2022/09/01 00:01,1,A,2,B,1.00,US Dollar,1.00,US Dollar,ACH,1",
            "2022/09/01 00:02,1,A,2",  # malformed
            "BEGIN LAUNDERING ATTEMPT - CYCLE:  Max 3 hops",  # previous block never closed
            "2022/09/01 00:03,001,A,002,B,1.00,US Dollar,1.00,US Dollar,ACH,1",
        ]
    )
    path = tmp_path / "p.txt"
    path.write_text(text + "\n")
    rows, report = parse_pattern_file(path)
    assert report.rows_outside_blocks == 1
    assert report.unknown_pattern_names == ["ZIGZAG"]
    assert report.malformed_rows == 1
    assert report.unclosed_blocks == 2
    assert report.schemes == 2
    assert rows["pattern_detail"].to_list() == [None, "Max 3 hops"]
    assert rows["from_bank"].to_list() == [1, 1]
