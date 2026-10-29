"""Week-10 checks on real data (skipped when absent): X4 part 1 and privacy accounting."""

from __future__ import annotations

import json

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir

DATASETS = ("HI-Medium", "LI-Medium")


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_x4_and_accounting(name: str) -> None:
    path = artifacts_dir() / "week10" / f"x4_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: X4 not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    s = r["summary"]
    for key in ("gbdt-local", "mlp-centralised", "mlp-local", "mlp-fedavg"):
        assert 0 < s[key]["auprc"]["estimate"] <= 1
    for seed in r["per_seed"]:
        for p in seed["privacy"].values():
            for client, rep in p["clients"].items():  # CC4: never above target
                assert rep["epsilon_spent"] <= rep["target_epsilon"] + 1e-6
                assert rep["steps_done"] == rep["steps_planned"]
                assert rep["delta"] < 1 / seed["clients"][client]  # δ below 1 / units
    ledger = artifacts_dir() / "week10" / f"privacy_ledger_{name}.jsonl"
    runs = {json.loads(line)["run"] for line in ledger.read_text().splitlines()}
    assert r["run_id"] in runs
