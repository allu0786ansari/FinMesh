"""Week-8 checks on real data (skipped when absent): X1-X3 and the leakage audit."""

from __future__ import annotations

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir

DATASETS = ("HI-Medium", "LI-Medium", "HI-Small", "LI-Small")


def _load(name: str) -> dict:  # type: ignore[type-arg]
    path = artifacts_dir() / "week08" / f"x1_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: week-8 X1 not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    return r


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_relational_oracle_and_sweeps(name: str) -> None:
    r = _load(name)
    s = r["summary"]
    assert r["h1b_ceiling"] == "oracle-relational"  # amendment A14
    rel, orc, s0 = (s[k]["linked"]["estimate"] for k in ("oracle-relational", "oracle", "S0"))
    assert rel > s0 and orc > s0
    for ceiling in ("oracle-relational", "oracle"):
        assert s["H1b"][ceiling]["S2/stacker"]["estimate"] is not None
    assert len(r["epsilons"]) == 5 and len(r["taus"]) == 3
    for seed in r["per_seed"]:
        p = seed["protocol"]
        assert all(v.get("service_refused", 0) == 0 for v in p.values()), "token budget"
        assert p["S1"]["accounts_disclosed"] == 0
        for tau in r["taus"]:  # PD never discloses more than S2
            assert p[f"PD[tau={tau}]"]["accounts_disclosed"] <= p["S2"]["accounts_disclosed"]
        for eps in r["epsilons"]:
            assert p[f"S3[eps={eps:g}]"]["ldp_max_account_epsilon"] <= 8.0 + 1e-9


@pytest.mark.real_data
@pytest.mark.parametrize("name", DATASETS)
def test_audit_is_complete(name: str) -> None:
    r = _load(name)
    a = r["audit"]
    assert a is not None and a["targets"]["test"] > 1000
    for target, res in a["attacks"].items():
        assert {"prior", "S1", "S2", "S4"} <= set(res), target
    a1 = a["A1"]
    check = a1["mechanism_check"]
    assert check["hash_matches"] == check["oprf_matches"] == check["checked"]
    assert a1["pooled"]["hash"] >= a1["pooled"]["oprf_sized"]
    assert "H1c" in a and "S1_and_S3_le2_within" in a["H1c"]
