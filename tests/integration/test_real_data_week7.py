"""Week-7 checks on real data (skipped when absent): X1 on validation."""

from __future__ import annotations

import math

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir

DATASETS = ("HI-Medium", "LI-Medium", "HI-Small", "LI-Small")
LEVELS = ("S1/stacker", "S2/stacker", "S4/stacker")


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_x1_is_complete_and_consistent(name: str) -> None:
    path = artifacts_dir() / "week07" / f"x1_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: X1 not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    assert r["primary_fusion"] == "stacker"  # amendment A13
    s = r["summary"]
    for name_ in ("S0", "oracle", "propagation", *LEVELS):
        assert name_ in s
        est = s[name_]["linked"]["estimate"]
        assert 0.0 <= est <= 1.0 and not math.isnan(est)
    # The oracle shows a linked gain over S0 (Gate G1), so recovery is defined.
    assert s["oracle"]["linked"]["estimate"] > s["S0"]["linked"]["estimate"]
    for level in LEVELS:
        assert s["H1b"][level]["estimate"] is not None
    # Every protocol run stayed inside the token budget.
    for seed in r["per_seed"]:
        for level, p in seed["protocol"].items():
            assert p.get("service_refused", 0) == 0, (seed["seed"], level)
            assert p["requests"] > 0
    assert len(r["seeds"]) >= 3
