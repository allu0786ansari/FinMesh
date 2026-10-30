"""Week 12: A19 grid, IID arm, saved models, membership audit, ensemble, Gate G3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from finmesh.training.data import Rows
from finmesh.training.dp_tune import choose, grid_settings
from finmesh.training.membership import empirical_epsilon, in_mask, tpr_at
from finmesh.training.neural import DpHparams
from finmesh.training.x5 import iid_partition, load_models, save_models


def test_a19_grid_has_equal_updates_and_a18_kept() -> None:
    a19 = grid_settings("A19")
    assert len(a19) == 18 and {s[3] for s in a19} == {20}  # same 1,000 updates everywhere
    assert {s[0] for s in a19} == {1.0, 3.0, 10.0} and {s[1] for s in a19} == {512, 2048}
    a18 = grid_settings("A18")
    assert len(a18) == 15 and {s[3] for s in a18} == {20, 5, 1}  # fixed example budget
    with pytest.raises(ValueError):
        grid_settings("A20")


def test_choose_breaks_ties_towards_cheaper() -> None:
    rows = [
        {"holdout_auprc": 0.4, "batch": 2048, "clip": 1.0, "lr": 1e-3},
        {"holdout_auprc": 0.4, "batch": 512, "clip": 3.0, "lr": 1e-3},
        {"holdout_auprc": 0.4, "batch": 512, "clip": 1.0, "lr": 1e-2},
        {"holdout_auprc": 0.3, "batch": 512, "clip": 1.0, "lr": 1e-3},
        {"holdout_auprc": float("nan"), "batch": 512, "clip": 1.0, "lr": 1e-3},
    ]
    best = choose(rows)
    assert best is not None and (best["batch"], best["clip"], best["lr"]) == (512, 1.0, 1e-2)
    assert choose([{"holdout_auprc": float("nan")}]) is None


def test_retune_keeps_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import finmesh.training.neural as neural

    path = tmp_path / "dp_hparams.json"
    monkeypatch.setattr(neural, "HPARAMS_PATH", path)
    neural.write_dp_hparams("HI-Small", DpHparams(1.0, 512, 1e-3, "dp-tune HI-Small"), {"g": 18})
    neural.write_dp_hparams(
        "HI-Small", DpHparams(3.0, 2048, 3e-3, "dp-tune HI-Small (A19)", 20), {"g": 19}
    )
    doc = json.loads(path.read_text())
    assert doc["regimes"]["HI"]["clip"] == 3.0 and doc["history"]["HI"][0]["clip"] == 1.0
    got = neural.dp_hparams("HI-Medium")
    assert (got.clip, got.batch, got.lr, got.local_steps) == (3.0, 2048, 3e-3, 20)


def _rows(n: int = 400) -> Rows:
    rng = np.random.default_rng(1)
    account = rng.integers(0, 60, n).astype(np.uint64)
    return Rows(
        x=rng.random((n, 2)).astype(np.float32),
        y=(rng.random(n) < 0.1).astype(np.int8),
        w=np.ones(n),
        member=(account % 3).astype(np.int64),
        account=account,
        window=rng.integers(0, 30, n),
    )


def test_iid_partition_keeps_sizes_and_accounts_whole() -> None:
    fit = _rows()
    iid = iid_partition(fit, 0)
    assert fit.account is not None

    def sizes(r: Rows) -> list[int]:
        assert r.account is not None
        return sorted(len(np.unique(r.account[r.member == m])) for m in np.unique(r.member))

    assert sizes(iid) == sizes(fit)  # each client keeps its number of accounts
    for a in np.unique(fit.account):  # an account's rows move together
        assert len(np.unique(iid.member[fit.account == a])) == 1
    assert not np.array_equal(iid.member, fit.member)  # something moved
    assert np.array_equal(iid_partition(fit, 0).member, iid.member)  # fixed by the seed
    assert iid.x is fit.x  # no copy of the features


def test_models_round_trip(tmp_path: Path) -> None:
    params = {"dp[account,cap16,eps=1]": [np.ones((3, 2)), np.zeros((3, 1))], "fedavg": [np.eye(2)]}
    got = load_models(save_models(tmp_path / "m" / "seed0.npz", params))
    assert set(got) == set(params)
    for k, v in params.items():
        assert all(np.array_equal(a, b) for a, b in zip(got[k], v, strict=True))


def test_tpr_at_fpr_never_exceeds_target() -> None:
    rng = np.random.default_rng(0)
    s_out = rng.normal(size=10_000)
    s_in = rng.normal(0.5, 1.0, size=10_000)
    one_in, one_out = np.ones(len(s_in)), np.ones(len(s_out))
    for fpr in (0.01, 0.001):
        tpr, achieved, _ = tpr_at(s_in, one_in, s_out, one_out, fpr)
        assert achieved <= fpr and tpr > achieved  # informative scores beat chance
    tied = np.zeros(1000)  # every score tied: nothing can be flagged without exceeding FPR
    tpr, achieved, _ = tpr_at(tied, np.ones(1000), tied, np.ones(1000), 0.01)
    assert tpr == 0.0 and achieved == 0.0
    s = rng.normal(size=20_000)  # a useless attack: TPR close to FPR
    tpr, _, _ = tpr_at(s[:10_000], one_in, s[10_000:], one_out, 0.05)
    assert abs(tpr - 0.05) < 0.02


def test_empirical_epsilon() -> None:
    assert empirical_epsilon(10, 10_000, 100, 10_000, 1e-6) == 0.0  # TPR below FPR: nothing
    strong = empirical_epsilon(5_000, 10_000, 10, 10_000, 1e-6)
    assert 5.0 < strong < np.log(0.5 / 0.001)  # conservative: below the point ratio


def test_in_mask_is_stable_and_balanced() -> None:
    acc = np.arange(20_000, dtype=np.uint64)
    mem = (acc % 8).astype(np.int64)
    m = in_mask(acc, mem)
    assert 0.48 < m.mean() < 0.52 and np.array_equal(m, in_mask(acc, mem))


def test_week12_pipelines_on_the_fixture(fixture_paths: object, ingested: object) -> None:
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.g3 import decide, render_g3
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import FeatureStore, build_features
    from finmesh.features.variants import degree_cap
    from finmesh.training.ensemble import run_ensemble
    from finmesh.training.ensemble_report import render_ensemble
    from finmesh.training.membership import run_membership
    from finmesh.training.membership_report import render_membership
    from finmesh.training.x5 import run_x5

    paths = fixture_paths
    run_g0(paths)  # type: ignore[arg-type]
    build_universe(paths, "B8")  # type: ignore[arg-type]
    build_features(paths, "B8")  # type: ignore[arg-type]
    build_features(paths, "B8", variant=degree_cap(3))  # type: ignore[arg-type]
    tmp = Path(FeatureStore(paths, "B8", "member").layout.root).parent / "w12"  # type: ignore[arg-type]

    x5 = run_x5(paths, tmp, seeds=(0,), reps=20, cap=3, rounds=3, local_steps=3)  # type: ignore[arg-type]
    assert set(x5["summary"]["iid"]) == {"nonprivate", "1", "3", "10"}
    saved = load_models(Path(x5["per_seed"][0]["models_file"]))
    assert "dp-iid[account,cap3,eps=3]" in saved and "fedavg[account,cap3]" in saved

    mia = run_membership(paths, tmp, cap=3, reps=20, rounds=3, local_steps=3)  # type: ignore[arg-type]
    assert mia["accounts"]["in"] > 0 and mia["accounts"]["out"] > 0
    for res in mia["results"].values():
        assert set(res["attacks"]) == {"LOSS", "REF"}
    for p in mia["privacy"].values():
        for rep in p["clients"].values():
            assert rep["epsilon_spent"] <= rep["target_epsilon"] + 1e-6
    assert "membership inference" in render_membership(mia)
    assert (tmp / "privacy_ledger_FIXTURE-Small.jsonl").exists()

    ens = run_ensemble(paths, x5, reps=20)  # type: ignore[arg-type]
    s = ens["summary"]
    assert {"dp1", "dp3", "dp10", "fedavg", "centralised"} <= set(s["gain_over_local"])
    assert "stacked ensemble" in render_ensemble(ens)

    # The gate's rule on rows shaped like summarise()'s output.
    row: dict[str, Any] = {
        "dataset": "HI-Medium",
        "ledger": {"entries": 3, "over_target": 0, "ok": True},
        "audit_violation": False,
        "mia": {"dp[account,capped,eps=1]": {"REF": {"estimate": 0.01}, "bound": 0.03}},
        "mia_power": {"REF": {"estimate": 0.6, "low": 0.55, "high": 0.65}},
        "ensemble": {
            "local": s["stack[local]"]["auprc"],
            "gains": s["gain_over_local"],
            "smallest_qualifying_epsilon": 3.0,
        },
    }
    assert decide([row])["decision"] == "DP scorer joins" and decide([row])["epsilon"] == 3.0
    assert "ε = 3" in render_g3([row], [])
    row["ensemble"]["smallest_qualifying_epsilon"] = None
    assert decide([row])["decision"] == "local ensemble"
    row["audit_violation"] = True
    assert decide([row])["decision"] == "blocked"
    row["audit_violation"], row["ledger"]["ok"] = False, False
    assert decide([row]) == {"decision": "blocked", "reason": "accounting", "epsilon": None}
