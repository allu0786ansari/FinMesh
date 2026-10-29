"""Week-9 checks on real data (skipped when absent): A16 fixes, attacks A4-A6, demo slice."""

from __future__ import annotations

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.matching.tokens import token_budget
from finmesh.paths import artifacts_dir

DATASETS = ("HI-Medium", "LI-Medium")


def _load(kind: str, name: str) -> dict:  # type: ignore[type-arg]
    path = artifacts_dir() / "week09" / f"{kind}_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: week-9 {kind} not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    return r


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_s3_always_answers_and_budgets_hold(name: str) -> None:
    r = _load("x1", name)
    budget = token_budget(name)
    for seed in r["per_seed"]:
        for level, p in seed["protocol"].items():
            assert p.get("service_refused", 0) == 0, (level, "sized budget too small")
            assert p.get("max_bank_epoch_queries", 0) <= budget
            if level.startswith("S3["):
                # A16: "no record" only when the account's epoch budget is spent
                assert p["responses"].get("no_record", 0) <= p.get("ldp_withheld", 0)


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_attacks_a4_to_a6(name: str) -> None:
    a = _load("x1", name)["audit"]
    a4 = a["A4"]
    assert a4["S2"]["queries"] > 100 and a4["S2"]["hit1"] > a4["S2"]["chance_hit1"]
    for level, v in a4.items():
        if level.startswith("S3[eps=0.5"):
            assert v["hit1"] < a4["S2"]["hit1"]  # fresh noise after rotation links less
    assert a["A5"]["rows"] > 1000
    assert a["A6"]["rows"] > 1000 and "gain_tpr_0.01" in a["A6"]["attack"]
    assert a["A1"]["protocol_budget"] == token_budget(name)


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_demo_slice(name: str) -> None:
    r = _load("demo_slice", name)
    assert r["sessions"] >= 20
    assert r["latency"]["p95"] is not None
    card = r["example"]
    assert card["requests"] > 0 and card["typology"]
