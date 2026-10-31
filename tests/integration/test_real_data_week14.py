"""Week-14 checks on real data (skipped when absent): coverage curve and the narrative (H3b)."""

from __future__ import annotations

import pytest

from finmesh.eval.coverage import COVERAGE_POINTS
from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir


def _load(week: str, kind: str, name: str) -> dict:  # type: ignore[type-arg]
    path = artifacts_dir() / week / f"{kind}_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: {kind} not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    return r


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
@pytest.mark.parametrize("p", COVERAGE_POINTS)
def test_coverage_point(name: str, p: int) -> None:
    r = _load("week09", "x1", f"{name}_B8c{p}")
    assert r["option"] == f"B8c{p}" and not r["sweeps"] and not r["audit"]
    assert r["seeds"] == [0, 1, 2] and "S2/stacker" in r["summary"]


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_narrative(name: str) -> None:
    r = _load("week14", "narrative", name)
    s = r["summary"]
    assert r["level"] == "S2" and r["seed"] == 0 and r["model"] == "llama3.2:3b"
    assert 0 < s["cases"] <= 200 and len(r["cases"]) == s["cases"]
    # The analyst never sees a model-chosen label: every final case keeps the assigned one.
    assert all(c["assigned"] in (c["top_prediction"], "UNATTRIBUTED") for c in r["cases"])
    assert s["H3b"]["grounding"]["estimate"] is not None
