"""Paper assets: built from the committed result pages, IEEE sizes, every number traceable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finmesh.paper import sources as S
from finmesh.paper.build import build_assets


def test_ci_parsing_and_missing_pages(tmp_path: Path) -> None:
    assert S.CI.parse("0.0674 [0.0239, 0.1218]") == S.CI(0.0674, 0.0239, 0.1218)
    assert S.CI.parse("-0.0044 [-0.0140, 0.0000]").lo == -0.014
    assert S.CI.parse("12,345") == S.CI(12345.0)
    with pytest.raises(S.MissingValue):
        S.CI.parse("—")
    with pytest.raises(S.MissingValue):
        S._read(tmp_path / "nope.md")


def test_tables_skip_their_header_rows() -> None:
    text = "## A\n\n| Level | x |\n| --- | --- |\n| S1 | 1 |\n| S2 | 2 |\n\nafter\n"
    assert S._rows(text, "## A") == [["S1", "1"], ["S2", "2"]]


def test_readers_on_the_committed_pages() -> None:
    lad = S.ladder("HI-Large-W16")
    assert lad["S2"].est == pytest.approx(0.5342) and lad["S0"].est == pytest.approx(0.0632)
    assert S.gain("LI-Large-W16", "_noart").est == pytest.approx(0.2101)
    assert S.attack_advantage("LI-Large-W16")["S1F[gate=2]"].est == pytest.approx(0.0038)
    assert S.verdict("LI-Large-W16", "H1c") is False and S.flag_within("LI-Large-W16") is True
    assert S.case_quality("HI-Large-W16")["alerts"] == (18.0, 152.6)
    assert S.dataset_stats("HI-Medium").test_multi_member == 480
    assert S.pt2("HI-Medium") == pytest.approx(19.86)


def test_build_writes_ieee_figures_tables_and_numbers(tmp_path: Path) -> None:
    import shutil

    from finmesh.paper.build import PAPER

    (tmp_path / "static").mkdir()
    shutil.copy(PAPER / "static" / "tab_related.tex", tmp_path / "static")
    r = build_assets(tmp_path)
    names = {Path(p).name for p in r["figures"]}
    assert {"fig_ladder.pdf", "fig_privacy.pdf", "fig_workload.pdf", "fig_robustness.pdf"} <= names
    tabs = {Path(p).name for p in r["tables"]}
    assert {"tab_results.tex", "tab_datasets.tex", "tab_related.tex"} <= tabs
    res = (tmp_path / "tables" / "tab_results.tex").read_text()
    assert r"\begin{table*}" in res and r"\caption{" in res.split(r"\begin{tabular}")[0]
    bench = (tmp_path / "tables" / "tab_benchmark.tex").read_text()
    assert "HI-Small & LI-Small & HI-Medium & LI-Medium" in bench and r"\textbf{" in bench
    numbers = json.loads((tmp_path / "assets.json").read_text())
    assert numbers["figures"]["ladder"]["HI-Large-W16"]["S2"]["est"] == pytest.approx(0.5342)
    from PIL import Image

    with Image.open(tmp_path / "figures" / "fig_ladder.png") as im:  # 3.5 in at 300 dpi
        assert abs(im.width / 300 - 3.5) < 0.35
