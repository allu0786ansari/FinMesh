from __future__ import annotations

from pathlib import Path

from finmesh.cli import main
from finmesh.data.accounts import load_accounts
from finmesh.data.fixture import FixtureTruth
from finmesh.data.profile import build_profile, render_markdown, write_profile
from finmesh.paths import DatasetPaths


def test_profile_numbers(
    fixture_paths: DatasetPaths, fixture_truth: FixtureTruth, ingested: dict[str, object]
) -> None:
    profile = build_profile(fixture_paths)
    s = profile["summary"]
    assert s["rows"] == fixture_truth.rows
    assert 10.0 < s["span_days"] <= 12.0  # ten dense days plus the sparse tail
    sch = profile["schemes"]
    assert sch["schemes"] == fixture_truth.schemes
    assert sch["multi_bank_schemes"] == fixture_truth.multi_bank_schemes
    expected_share = fixture_truth.pattern_rows / fixture_truth.laundering_rows
    assert abs(sch["pattern_labelled_share"] - expected_share) < 1e-9
    assert profile["entities"]["entities_with_accounts_at_2plus_banks"] > 0
    banks = {b["bank"]: b for b in profile["banks_top"]}
    assert {1, 10, 12, 70, 220, 1124} <= set(banks)
    total_touch_laundering = sum(b["touching_laundering"] for b in profile["banks_top"])
    assert total_touch_laundering >= fixture_truth.laundering_rows  # cross-bank rows count twice

    md = render_markdown(profile)
    assert "| 1124 |" in md  # bank ids are not formatted as numbers
    for heading in (
        "### Data quality",
        "### Schemes from the pattern file",
        "### Entities across banks",
    ):
        assert heading in md


def test_write_profile(
    fixture_paths: DatasetPaths, ingested: dict[str, object], tmp_path: Path
) -> None:
    artifact, report = write_profile(fixture_paths, tmp_path / "p.md")
    assert artifact.exists()
    assert report is not None and "fixture=True" in report.read_text()


def test_accounts_loader_tolerance(tmp_path: Path) -> None:
    assert load_accounts(tmp_path / "missing.csv") is None
    bad = tmp_path / "bad.csv"
    bad.write_text("Name,Number\nx,1\n")
    assert load_accounts(bad) is None


def test_cli_end_to_end(data_env: Path, capsys: object) -> None:
    assert main(["fixture", "--seed", "7"]) == 0
    assert main(["week1", "--dataset", "FIXTURE-Small"]) == 0
    assert main(["check"]) == 0
    assert (data_env / "artifacts" / "week01" / "data_profile_FIXTURE-Small.md").exists()
