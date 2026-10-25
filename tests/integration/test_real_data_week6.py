"""Week-6 checks on real data (skipped when absent): the sharing protocol run."""

from __future__ import annotations

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir

DATASETS = ("HI-Medium", "LI-Medium", "HI-Small", "LI-Small")


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_sharing_run_is_consistent(name: str) -> None:
    path = artifacts_dir() / "week06" / f"sharing_{name}_seed0.json"
    if not path.exists():
        pytest.skip(f"{name}: sharing run not done")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    primary = r["primary_budget"]

    def linked(level: str) -> float:
        b = next(x for x in r["results"][level]["budgets"] if x["budget"] == primary)
        return float(b["linked"]["estimate"])

    # Sharing only adds links; it never links more than the pooled rule on the same alerts.
    assert linked("S1") >= linked("S0")
    assert linked("S1") <= linked("S0+pooled-link") + 1e-9
    assert linked("S2") == pytest.approx(linked("S1"))  # week 6: same links by design
    for level in ("S1", "S2"):
        p = r["protocol"][level]
        assert p["service_refused"] == 0, "token budget too small"
        assert p["cross_member_incidents"] > 0, "done-when: cross-bank incidents exist"
