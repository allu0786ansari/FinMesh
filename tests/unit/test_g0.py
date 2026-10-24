from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from finmesh.cli import main
from finmesh.data.consortium import ConsortiumSpec
from finmesh.data.fixture import FixtureTruth
from finmesh.eval.g0 import (
    CASE_STUDY_THRESHOLD,
    PROCEED_THRESHOLD,
    OptionResult,
    band,
    render,
    render_summary,
    run_g0,
    select_option,
)
from finmesh.paths import DatasetPaths


def _result(option: str, projected: float) -> OptionResult:
    return OptionResult(
        spec=ConsortiumSpec.parse(option),
        members=8,
        member_account_share=1.0,
        visible_tx_share=1.0,
        multi_member={"train": 0, "val": 0},
        visible={"train": 0, "val": 0},
        legs={},
        projected_test_multi_member=projected,
    )


def test_bands() -> None:
    assert band(PROCEED_THRESHOLD) == "proceed"
    assert band(PROCEED_THRESHOLD - 1) == "case_study_pooled"
    assert band(CASE_STUDY_THRESHOLD) == "case_study_pooled"
    assert band(CASE_STUDY_THRESHOLD - 1) == "fallback"


def test_selection_prefers_smallest_sufficient_real_bank_option() -> None:
    results = [_result("A8", 20), _result("A16", 120), _result("A32", 300), _result("B8", 500)]
    spec, reason = select_option(results)
    assert spec.name == "A16"
    assert "smallest real-bank option" in reason


def test_selection_falls_back_to_b8() -> None:
    results = [_result("A8", 3), _result("A64", 99), _result("B4", 400), _result("B8", 200)]
    spec, _ = select_option(results)
    assert spec.name == "B8"


def test_run_g0_on_fixture(
    fixture_paths: DatasetPaths, fixture_truth: FixtureTruth, ingested: dict[str, object]
) -> None:
    result = run_g0(fixture_paths)
    assert result["window_hours"] == 6
    assert result["schemes_total"] == fixture_truth.schemes
    assert result["schemes_truncated"] == fixture_truth.truncated_schemes
    assert result["observation_window"]["rows_after"] == fixture_truth.tail_rows
    assigned = {r["partition"]: r["schemes"] for r in result["schemes_by_partition"]}
    assert sum(assigned.values()) == fixture_truth.schemes

    options = {o["option"]: o for o in result["options"]}
    assert set(options) == {"A8", "A16", "A32", "A64", "B4", "B8", "B16"}
    # Grouped options cover every account; real-bank options do not when banks are many.
    assert options["B8"]["member_account_share"] == 1.0
    assert options["A8"]["member_account_share"] < 1.0
    # Train and val counts never exceed the schemes assigned there.
    for o in options.values():
        assert o["multi_member"]["train"] <= assigned.get("train", 0)
        assert o["visible"]["train"] >= o["multi_member"]["train"]
        # No test numbers are computed for the options (only for the chosen one).
        assert "test" not in o["multi_member"]

    assert result["selection"]["option"] == "B8"  # fixture is far below 100 schemes
    assert result["test"]["option"] == "B8"
    assert result["test"]["band"] == band(result["test"]["multi_member_schemes"])
    assert (fixture_paths.parquet / "membership_B8.parquet").exists()
    split = pl.read_parquet(fixture_paths.parquet / "split_w6.parquet")
    assert split.height == fixture_truth.rows

    md = render(result)
    assert "# G0 evidence · FIXTURE-Small" in md
    assert "## Federation options (train and validation only)" in md
    summary = render_summary([result, {**result, "dataset": "OTHER"}])
    assert "Pooled across datasets" in summary


def test_g0_cli_writes_fixture_report_outside_docs(data_env: Path) -> None:
    assert main(["fixture"]) == 0
    assert main(["week1", "--dataset", "FIXTURE-Small"]) == 0
    assert main(["g0", "--dataset", "FIXTURE-Small"]) == 0
    report = data_env / "artifacts" / "week02" / "G0_evidence_FIXTURE-Small.md"
    assert report.exists()
    artifact = json.loads((data_env / "artifacts" / "week02" / "g0_FIXTURE-Small.json").read_text())
    assert artifact["provenance"]["fixture"] is True
    assert main(["feature-timing", "--dataset", "FIXTURE-Small"]) == 0
    assert main(["feature-timing", "--dataset", "FIXTURE-Small", "--option", "A8"]) == 0
