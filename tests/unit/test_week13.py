"""Week 13: attribution by sharing level (X6) and the real-bank federation path (A20)."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from finmesh.training.x6 import (
    LEVELS,
    METHODS,
    attribute,
    best_incident,
    catalogue_predict,
    combine,
    incident_features,
    load_catalogue,
    rule_predict,
    shape,
)

COLS = ("fan_out", "fan_in", "pass_through", "tx_out", "tx_in", "amt_out", "amt_in",
        "cross_bank_share", "new_cp_share", "in_out_delay_min_h", "gs_min_fan", "cyc2", "cyc3",
        "cyc4", "sg_out_max", "sg_in_max")  # fmt: skip


def test_catalogue_is_complete_and_consistent() -> None:
    cat = load_catalogue()
    ids = [e["id"] for e in cat["entries"]]
    assert sorted(ids) == sorted(
        [
            "FAN-OUT",
            "FAN-IN",
            "GATHER-SCATTER",
            "SCATTER-GATHER",
            "CYCLE",
            "RANDOM",
            "BIPARTITE",
            "STACK",
        ]
    )
    for e in cat["entries"]:
        assert set(e["signature"]) <= set(cat["shape_features"]) and e["stage"] in cat["stages"]
        assert e["red_flags"] and e["review_actions"]
    rule_patterns = {r["pattern"] for r in cat["rules"]["order"]} | {cat["rules"]["otherwise"]}
    assert rule_patterns <= set(ids)


def test_best_incident_takes_most_accounts_then_rows_then_lowest_id() -> None:
    sw = pl.DataFrame(
        {
            "scheme_id": [1, 1, 1, 1, 2, 2],
            "member": [0, 0, 1, 1, 0, 0],
            "account": [10, 11, 12, 12, 20, 21],
            "window": [5, 5, 5, 6, 7, 7],
        }
    )
    inc = pl.DataFrame(
        {
            "member": [0, 0, 1, 1, 0, 0],
            "account": [10, 11, 12, 12, 20, 21],
            "window": [5, 5, 5, 6, 7, 7],
            "incident": [3, 3, 4, 4, 8, 9],
        }
    )
    got = dict(
        zip(
            *best_incident(sw, inc).sort("scheme_id").to_dict(as_series=False).values(), strict=True
        )
    )
    assert got == {1: 3, 2: 8}  # scheme 1: two accounts beat one account in two rows; 2: low id


def _incident() -> tuple[pl.DataFrame, np.ndarray, np.ndarray]:
    inc = pl.DataFrame(
        {
            "member": [0, 0, 0, 1, 1],
            "account": [1, 2, 2, 3, 4],
            "window": [10, 10, 11, 11, 12],
            "incident": [0, 0, 0, 0, 0],
            "pos": [0, 1, 2, 3, 4],
        }
    )
    rng = np.random.default_rng(0)
    x = rng.integers(0, 30, (5, len(COLS))).astype(float)
    x[0, 0] = np.nan  # missing values are ignored by the aggregates
    return inc, x, x * 10


def test_each_level_sees_only_what_it_should(monkeypatch: pytest.MonkeyPatch) -> None:
    inc, x, xp = _incident()
    s0 = incident_features("S0", inc, x, xp, COLS, 0)
    assert s0["own_rows"][0] == 3 and s0["own_accounts"][0] == 2  # owner = member 0
    assert s0["own_max_fan_out"][0] == np.nanmax(x[:3, 0])  # NaN skipped
    assert not any(c.startswith(("rec_", "n_members", "all_")) for c in s0.columns)
    s1 = incident_features("S1", inc, x, xp, COLS, 0)
    assert s1["n_members"][0] == 2 and s1["n_accounts"][0] == 4 and s1["span"][0] == 3
    assert not any(c.startswith("rec_") for c in s1.columns)
    s2 = incident_features("S2", inc, x, xp, COLS, 0)
    rec = [c for c in s2.columns if c.startswith("rec_")]
    assert len(rec) == 20  # 10 counters, mean and max, from member 1's two rows only
    s3 = incident_features("S3", inc, x, xp, COLS, 0)
    assert set(rec) <= set(s3.columns)
    orc = incident_features("oracle", inc, x, xp, COLS, 0)
    assert orc["all_max_fan_in"][0] == np.nanmax(xp[:, 1]) and orc["n_members"][0] == 2


def _sig(**kw: float) -> np.ndarray:
    names = load_catalogue()["shape_features"]
    return np.array([[kw.get(n, 0.0) for n in names]])


def test_rules_follow_the_catalogue_order() -> None:
    cat = load_catalogue()
    cases = {
        "CYCLE": _sig(cycles=1, fan_out=5),
        "SCATTER-GATHER": _sig(scatter_gather=3),
        "GATHER-SCATTER": _sig(gather_scatter=2),
        "BIPARTITE": _sig(fan_in=4, fan_out=4),
        "FAN-OUT": _sig(fan_out=6),
        "FAN-IN": _sig(fan_in=6),
        "STACK": _sig(pass_through=0.9, accounts=5),
        "RANDOM": _sig(pass_through=0.9, accounts=2),
    }
    for want, sig in cases.items():
        assert rule_predict(sig, cat)[0] == want
    nan = _sig()
    nan[:] = np.nan
    assert rule_predict(nan, cat)[0] == "RANDOM"  # missing evidence falls through


def test_catalogue_matching_picks_the_nearest_signature() -> None:
    cat = load_catalogue()
    names = cat["shape_features"]
    rng = np.random.default_rng(1)
    train = rng.normal(0, 1, (200, len(names)))
    fan_out = np.zeros((1, len(names)))
    fan_out[0, names.index("fan_out")], fan_out[0, names.index("fan_in")] = 4, -4
    assert catalogue_predict(fan_out, train, cat)[0] == "FAN-OUT"
    cyc = np.zeros((1, len(names)))
    cyc[0, names.index("cycles")], cyc[0, names.index("pass_through")] = 4, 4
    assert catalogue_predict(cyc, train, cat)[0] == "CYCLE"


def _table(n: int = 240, seed: int = 0) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    pats = np.array(["FAN-IN", "FAN-OUT", "CYCLE"])[rng.integers(0, 3, n)]

    def f(p: str, name: str) -> float:
        base = {"FAN-IN": (8, 1, 0), "FAN-OUT": (1, 8, 0), "CYCLE": (2, 2, 3)}[p]
        return {"fan_in": base[0], "fan_out": base[1], "cyc2": base[2]}.get(name, 0) + rng.random()

    data: dict[str, object] = {
        "scheme_id": np.arange(n),
        "pattern": pats,
        "fold": (np.arange(n) >= n // 2).astype(np.int8),
        "incident": [None if i % 10 == 0 else i for i in range(n)],  # every 10th undetected
        "own_accounts": rng.integers(1, 5, n).astype(float),
        "own_mean_pass_through": rng.random(n),
    }
    for c in ("fan_in", "fan_out", "gs_min_fan", "cyc2", "cyc3", "cyc4", "sg_out_max", "sg_in_max"):
        data[f"own_max_{c}"] = [f(p, c) for p in pats]
    return pl.DataFrame(data)


def test_attributor_learns_and_undetected_schemes_get_no_prediction() -> None:
    t = _table()
    preds = attribute(t, "S0", 0, load_catalogue())
    det = t["incident"].is_not_null().to_numpy()
    y = t["pattern"].to_numpy()
    for m in METHODS:
        assert all(p is None for p in preds[m][~det])
        assert all(p is not None for p in preds[m][det])
    acc = (preds["attributor"][det] == y[det]).mean()
    maj = (preds["majority"][det] == y[det]).mean()
    assert acc > 0.9 and acc > maj
    sig = shape(t, "S0")
    assert sig.shape == (t.height, 8) and np.all(sig[:, -1] == 1)  # S0: one member


def _per_seed(correct_s0: float, correct_s2: float, n: int = 400) -> list[dict[str, object]]:
    rng = np.random.default_rng(3)
    pats = np.array(["FAN-IN", "FAN-OUT"])[rng.integers(0, 2, n)]
    other = np.where(pats == "FAN-IN", "FAN-OUT", "FAN-IN")
    seeds = []
    for s in range(2):
        levels = {}
        for lv in LEVELS:
            p = correct_s2 if lv in ("S2", "S3", "oracle") else correct_s0
            ok = rng.random(n) < p
            att = np.where(ok, pats, other).tolist()
            levels[lv] = {
                "scheme_id": list(range(n)),
                "pattern": pats.tolist(),
                "detected": [True] * n,
                "predictions": {
                    "attributor": att,
                    "majority": ["FAN-IN"] * n,
                    "rules": other.tolist(),
                    "catalogue": other.tolist(),
                },
            }
        seeds.append({"seed": s, "levels": levels})
    return seeds


def test_combine_judges_h3a_from_paired_scheme_bootstrap() -> None:
    better = combine(_per_seed(0.55, 0.85), reps=300)  # type: ignore[arg-type]
    assert better["H3a"]["met_on_validation"]
    assert better["levels"]["S2"]["attributor"]["accuracy"]["estimate"] > 0.8
    assert better["comparisons"]["S2-S0"]["low"] > 0
    same = combine(_per_seed(0.7, 0.7), reps=300)  # type: ignore[arg-type]
    assert not same["H3a"]["met_on_validation"]
    assert not same["stages"]["reported"]  # every AMLworld pattern maps to layering


def test_x6_and_the_real_bank_path_on_the_fixture(fixture_paths: object, ingested: object) -> None:
    from finmesh.data.consortium import ConsortiumSpec, bank_sizes, build_membership
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.training.x1 import run_x1
    from finmesh.training.x6 import run_x6
    from finmesh.training.x6_report import render_x6

    paths = fixture_paths
    run_g0(paths)  # type: ignore[arg-type]
    build_universe(paths, "B8")  # type: ignore[arg-type]
    build_features(paths, "B8")  # type: ignore[arg-type]
    build_features(paths, "B8", "pooled")  # type: ignore[arg-type]
    r = run_x6(paths, seeds=(0,), reps=50)  # type: ignore[arg-type]
    assert set(r["summary"]["levels"]) == set(LEVELS)
    assert r["summary"]["schemes"] == len(r["per_seed"][0]["levels"]["S0"]["pattern"])
    assert "pattern attribution" in render_x6(r)

    # A real-bank federation: membership, labels, both feature views, X1 without sweeps or audit.
    sizes = bank_sizes(paths.transactions)  # type: ignore[attr-defined]
    m = build_membership(sizes, ConsortiumSpec.parse("A8"))
    m.write_parquet(paths.parquet / "membership_A8.parquet")  # type: ignore[attr-defined]
    assert m.height == 8
    build_universe(paths, "A8")  # type: ignore[arg-type]
    build_features(paths, "A8")  # type: ignore[arg-type]
    build_features(paths, "A8", "pooled")  # type: ignore[arg-type]
    x = run_x1(paths, option="A8", seeds=(0,), reps=20, sweeps=False, audit=False)  # type: ignore[arg-type]
    assert x["option"] == "A8" and "S2/stacker" in x["summary"]


def test_option_tag_keeps_the_frozen_b8_names() -> None:
    from finmesh.cli import option_tag

    assert option_tag("HI-Medium", "B8") == "HI-Medium"
    assert option_tag("HI-Medium", "A64") == "HI-Medium_A64"
