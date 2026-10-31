"""Week-13 checks on real data (skipped when absent): X6 and the A64 real-bank check."""

from __future__ import annotations

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir
from finmesh.training.x6 import LEVELS


def _load(week: str, kind: str, name: str) -> dict:  # type: ignore[type-arg]
    path = artifacts_dir() / week / f"{kind}_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: {kind} not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    return r


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_x6(name: str) -> None:
    r = _load("week13", "x6", name)
    s = r["summary"]
    assert set(s["levels"]) == set(LEVELS) and s["schemes"] > 50 and r["seeds"] == [0, 1, 2]
    assert s["levels"]["oracle"]["detected_share"] > 0.5


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_x1_real_banks(name: str) -> None:
    r = _load("week09", "x1", f"{name}_A64")
    assert r["option"] == "A64" and not r["sweeps"] and r["seeds"] == [0, 1, 2]
    assert "S2/stacker" in r["summary"]
    b8 = _load("week09", "x1", name)  # the frozen headline is untouched
    assert b8["option"] == "B8"
