"""Week 7: triage features, fusion rules, the cross-fitted stacker, seed combining."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from finmesh.fusion.triage import (
    COMMON,
    S2_EXTRA,
    S4_EXTRA,
    evidence_features,
    feature_names,
    k_of_n,
    noisy_or,
)
from finmesh.paths import DatasetPaths
from finmesh.sharing.evidence import S4_FIELDS, WIRE_FIELDS
from finmesh.training.x1 import _halves, _recovery, combine, stacker_scores

KEY = {"member": pl.Int32, "account": pl.UInt64, "window": pl.Int32}


def _record(prob_bucket: int, fan_in: int = 0) -> list[int]:
    v = [0] * len(S4_FIELDS)
    v[S4_FIELDS.index("prob_bucket")] = prob_bucket
    v[S4_FIELDS.index("c_fan_in")] = fan_in
    v[S4_FIELDS.index("dev1_magnitude")] = 2
    v[S4_FIELDS.index("emb0")] = 150
    return v


def _case() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    candidates = pl.DataFrame(
        {"member": [0, 0, 1], "account": [1, 2, 3], "window": [5, 5, 6], "prob": [0.2, 0.01, 0.05]},
        schema={**KEY, "prob": pl.Float64},
    )
    responses = pl.DataFrame(
        [
            (0, 5, [1, 2], 1, 30, "ok", True, _record(4, 3)),
            (0, 5, [1], 2, 31, "no_record", False, None),
            (0, 5, [2], 3, 32, "refused", False, None),
        ],
        schema={
            "member": pl.Int32,
            "window": pl.Int32,
            "accounts": pl.List(pl.UInt64),
            "cp_member": pl.Int32,
            "cp": pl.UInt64,
            "status": pl.String,
            "alert": pl.Boolean,
            "record": pl.List(pl.Int64),
        },
        orient="row",
    )
    inbound = pl.DataFrame(
        {"member": [1, 1], "account": [3, 3], "window": [6, 6], "bucket": [2, 4]},
        schema={**KEY, "bucket": pl.Int8},
    )
    asked = pl.DataFrame(
        [(0, 5, [1, 2], 1), (0, 5, [1], 1), (0, 5, [2], 1)],
        schema={
            "member": pl.Int32,
            "window": pl.Int32,
            "accounts": pl.List(pl.UInt64),
            "n": pl.Int32,
        },
        orient="row",
    )
    return candidates, responses, inbound, asked


def test_feature_sets_grow_with_the_level() -> None:
    assert feature_names("S1") == COMMON
    assert feature_names("S2") == (*COMMON, *S2_EXTRA)
    assert feature_names("S4") == (*COMMON, *S2_EXTRA, *S4_EXTRA)
    assert len(S4_FIELDS) == len(WIRE_FIELDS) + len(S4_EXTRA)


def test_evidence_features_aggregate_responses_and_inbound_requests() -> None:
    candidates, responses, inbound, asked = _case()
    f = evidence_features("S4", candidates, responses, inbound, asked).sort("account")
    a1, a2, a3 = f.row(0, named=True), f.row(1, named=True), f.row(2, named=True)
    assert (a1["n_req"], a1["n_cp_alert"], a1["n_cp_record"], a1["n_refused"]) == (2, 1, 1, 0)
    assert a1["max_cp_prob"] == 4 and a1["max_cp_fan_in"] == 3 and a1["max_cp_dev"] == 2
    assert a1["cp_emb0"] == pytest.approx(1.5)
    assert (a2["n_req"], a2["n_refused"], a2["n_cp_alert"]) == (2, 1, 1)
    assert (a3["n_req"], a3["inbound_n"], a3["inbound_max"]) == (0, 2, 4)  # only asked about
    assert a1["own_logit"] == pytest.approx(np.log(0.2 / 0.8))
    s1 = evidence_features(
        "S1", candidates, responses.with_columns(pl.lit(None).alias("record")), inbound, asked
    )
    assert set(s1.columns) == {"member", "account", "window", "prob", *COMMON}


def test_noisy_or_and_k_of_n() -> None:
    candidates, responses, inbound, asked = _case()
    f = evidence_features("S2", candidates, responses, inbound, asked).sort("account")
    s1 = noisy_or(f, "S1", 0.5)
    assert s1[0] == pytest.approx(1 - 0.8 * 0.5)  # one flag
    assert s1[2] == pytest.approx(0.05)  # nothing received
    s2 = noisy_or(f, "S2", 0.5)
    assert s2[0] == pytest.approx(1 - 0.8 * 0.5 * (1 - 0.75))  # flag and a bucket-4 record
    k = k_of_n(f)
    assert k[1] > k[2] and k[0] > k[2]  # flagged candidates first


def test_stacker_never_uses_a_rows_own_fold() -> None:
    rng = np.random.default_rng(0)
    n = 4000
    x = rng.normal(size=n)
    label = (x + rng.normal(scale=0.5, size=n) > 1.5).astype(int)
    feats = pl.DataFrame({"member": np.zeros(n, dtype=np.int32), "prob": np.full(n, 0.1), "f": x})
    fold = (np.arange(n) >= n // 2).astype(np.int8)
    usable = np.ones(n, dtype=bool)
    a = stacker_scores(feats, ("f",), label, usable, fold, 0)
    shuffled = label.copy()
    shuffled[fold == 0] = rng.permutation(shuffled[fold == 0])
    b = stacker_scores(feats, ("f",), shuffled, usable, fold, 0)
    assert np.allclose(a[fold == 0], b[fold == 0])  # fold-0 rows are scored by a fold-1 model
    assert not np.allclose(a[fold == 1], b[fold == 1])
    ranks = np.argsort(np.argsort(a)), np.argsort(np.argsort(x))
    assert np.corrcoef(*ranks)[0, 1] > 0.99  # monotone in the signal (logistic)


def test_halves_split_validation_windows() -> None:
    assert _halves(np.array([39, 44, 45, 50]), 39, 50).tolist() == [0, 0, 1, 1]


def _outcomes(linked: list[bool]) -> pl.DataFrame:
    n = len(linked)
    return pl.DataFrame(
        {
            "scheme_id": list(range(n)),
            "linked": linked,
            "detected": [True] * n,
            "linked_cross_member": linked,
        }
    )


def test_combine_and_recovery() -> None:
    seeds = []
    for _ in range(2):
        seeds.append(
            {
                "outcomes": {
                    "S0": _outcomes([False] * 10),
                    "oracle": _outcomes([True] * 8 + [False] * 2),
                    "S1/stacker": _outcomes([True] * 4 + [False] * 6),
                    "S2/stacker": _outcomes([True] * 6 + [False] * 4),
                    "S4/stacker": _outcomes([True] * 6 + [False] * 4),
                },
                "auprc": {
                    "S0": 0.1,
                    "oracle": 0.3,
                    "S1/stacker": 0.2,
                    "S2/stacker": 0.2,
                    "S4/stacker": 0.2,
                },
            }
        )
    out = combine(seeds, reps=200)
    assert out["S2/stacker"]["linked"]["estimate"] == pytest.approx(0.6)
    assert out["S2/stacker"]["linked_gain"]["difference"]["estimate"] == pytest.approx(0.6)
    assert out["H1b"]["oracle"]["S2/stacker"]["estimate"] == pytest.approx(0.75)
    assert out["H1b"]["oracle"]["S1/stacker"]["estimate"] == pytest.approx(0.5)
    assert "oracle-relational" not in out["H1b"]  # not in these outcomes
    stack = {
        n: {
            "linked": np.column_stack(
                [s["outcomes"][n]["linked"].to_numpy() for s in seeds]
            ).astype(float)
        }
        for n in ("S0", "oracle", "S2/stacker")
    }
    assert _recovery(stack, "S2/stacker", 100)["estimate"] == pytest.approx(0.75)  # type: ignore[arg-type]


def test_x1_pipeline_on_the_fixture(
    fixture_paths: DatasetPaths,
    ingested: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """End to end with a budget large enough to alert on the small fixture."""
    import finmesh.training.x1 as x1
    from finmesh.eval.budgets import Budget
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.training.x1_report import (
        frontier_figure,
        ladder_figure,
        render_audit,
        render_x1,
        render_x3,
        x3_figure,
    )

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    build_features(fixture_paths, "B8", view="pooled")
    monkeypatch.setattr(x1, "PRIMARY", Budget("per_1000_per_day", 300.0))
    r = x1.run_x1(fixture_paths, seeds=(0, 1), reps=50, window_reps=20)
    s = r["summary"]
    expected = {"S0", "oracle", "oracle-relational", "oracle+propagation", "propagation"} | {
        f"{lv}/{f}" for lv in ("S1", "S2", "S4") for f in ("stacker", "noisy_or", "kofn")
    }
    expected |= {f"{n}/stacker" for n, _, _ in x1.level_runs(True)}
    assert expected <= set(s)
    assert s["oracle"]["linked"]["estimate"] > 0
    assert set(s["H1b"]) == {"oracle-relational", "oracle"}
    assert {"S1", "PD[tau=2]", "PD[tau=3]", "PD[tau=4]"} <= set(s["H1d"])
    runs = {n for n, _, _ in x1.level_runs(True)}
    for seed in r["per_seed"]:
        assert seed["candidates"] > 0 and seed["alerts"] > 0
        assert set(seed["protocol"]) == runs
        assert all(p["requests"] > 0 for p in seed["protocol"].values())
        assert seed["protocol"]["S1"]["accounts_disclosed"] == 0
        assert (
            seed["protocol"]["PD[tau=4]"]["accounts_disclosed"]
            <= seed["protocol"]["S2"]["accounts_disclosed"]
        )
        assert seed["protocol"]["S3[eps=8]"]["ldp_max_account_epsilon"] <= 8.0 + 1e-9
    audit = r["audit"]
    assert set(audit["attacks"]) == {
        "A2_third_party",
        "A3_amount_top",
        "A3_fan_in_top",
        "A3_pass_through",
    }
    assert {"prior", "S1", "S2", "S4"} <= set(audit["attacks"]["A2_third_party"])
    a1 = audit["A1"]
    assert a1["pooled"]["hash"] >= a1["pooled"]["oprf_sized"]
    check = a1["mechanism_check"]
    assert check["hash_matches"] == check["oprf_matches"] == check["checked"] > 0
    import json

    json.loads(json.dumps(r), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert "H1b on validation" in render_x1(r, "f.png")
    assert "PD: recall versus disclosure volume" in render_x3(r, "x3.png")
    page = render_audit(r, "frontier.png")
    assert "A1 token re-identification" in page and "H1c on validation" in page
    assert ladder_figure(r, tmp_path / "l.png").stat().st_size > 1000
    assert x3_figure(r, tmp_path / "x3.png") is not None
    assert frontier_figure(r, tmp_path / "f.png").stat().st_size > 1000  # type: ignore[union-attr]
