"""Week-12 checks on real data (skipped when absent): A19 tuning, X5, membership, ensemble."""

from __future__ import annotations

import pytest

from finmesh.eval.g3 import ledger_check
from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir
from finmesh.training.neural import dp_hparams


def _load(kind: str, name: str) -> dict:  # type: ignore[type-arg]
    path = artifacts_dir() / "week12" / f"{kind}_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: {kind} not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    return r


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Small", "LI-Small"])
def test_a19_tuning(name: str) -> None:
    r = _load("dp_tune", name)
    assert r["grid_name"] == "A19" and len(r["grid"]) == 18 and r["best"] is not None
    assert all(g["local_steps"] == 20 for g in r["grid"])
    hp = dp_hparams(name.replace("Small", "Medium"))
    assert "A19" in hp.source
    assert (hp.clip, hp.batch, hp.lr) == (r["best"]["clip"], r["best"]["batch"], r["best"]["lr"])


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_x5_a19(name: str) -> None:
    r = _load("x5", name)
    assert "A19" in r["hparams"]["source"] and r["iid"]
    assert set(r["summary"]["iid"]) == {"nonprivate", "1", "3", "10"}
    for seed in r["per_seed"]:
        assert seed["models_file"]
        for p in seed["privacy"].values():
            for rep in p["clients"].values():
                assert rep["epsilon_spent"] <= rep["target_epsilon"] + 1e-6


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_membership(name: str) -> None:
    r = _load("membership", name)
    assert r["accounts"]["in"] > 1000 and r["accounts"]["out"] > 1000
    assert len(r["results"]) == 4
    assert ledger_check(name)["ok"]


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_ensemble(name: str) -> None:
    r = _load("ensemble", name)
    x5 = _load("x5", name)
    assert r["x5_run"] == x5["run_id"] and r["seeds"] == x5["seeds"]
    assert {"dp1", "dp3", "dp10"} <= set(r["summary"]["gain_over_local"])
