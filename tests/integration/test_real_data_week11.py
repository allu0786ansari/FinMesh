"""Week-11 checks on real data (skipped when absent): tuning, influence, X5."""

from __future__ import annotations

import pytest

from finmesh.eval.provenance import read_artifact
from finmesh.paths import artifacts_dir
from finmesh.training.neural import dp_hparams


def _load(kind: str, name: str) -> dict:  # type: ignore[type-arg]
    path = artifacts_dir() / "week11" / f"{kind}_{name}.json"
    if not path.exists():
        pytest.skip(f"{name}: {kind} not run")
    prov, r = read_artifact(path)
    assert not prov["fixture"]
    return r


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Small", "LI-Small"])
def test_tuning_chose_a_setting(name: str) -> None:
    r = _load("dp_tune", name)
    assert len(r["grid"]) == 15 and r["best"] is not None
    hp = dp_hparams(name.replace("Small", "Medium"))
    assert (hp.clip, hp.batch) == (r["best"]["clip"], r["best"]["batch"])


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_influence(name: str) -> None:
    r = _load("influence", name)
    member, capped = r["views"]["member"], r["views"][f"cap{r['cap']}"]
    assert r["sample"] == 200 and member["changed_accounts"] > 0
    assert capped["group_size"]["q99"] <= member["group_size"]["q99"]


@pytest.mark.real_data
@pytest.mark.parametrize("name", ["HI-Medium", "LI-Medium"])
def test_x5(name: str) -> None:
    r = _load("x5", name)
    assert r["hparams"]["source"].startswith("dp-tune")
    assert set(r["summary"]["H2b"]) == {"1", "3", "10"}
    for seed in r["per_seed"]:
        for p in seed["privacy"].values():
            for rep in p["clients"].values():
                assert rep["epsilon_spent"] <= rep["target_epsilon"] + 1e-6
