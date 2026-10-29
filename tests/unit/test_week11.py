"""Week 11: account bags, DP settings file, degree-cap and removal variants, influence."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from finmesh.features.variants import degree_cap, remove_accounts
from finmesh.training.data import Rows
from finmesh.training.neural import (
    BAG_CAP,
    DpHparams,
    client_data,
    dp_hparams,
    regime,
)


def _rows() -> Rows:
    rng = np.random.default_rng(0)
    n = 300
    account = rng.integers(0, 20, n).astype(np.uint64)
    return Rows(
        x=rng.random((n, 3)).astype(np.float32),
        y=(rng.random(n) < 0.1).astype(np.int8),
        w=np.ones(n),
        member=np.where(account < 10, 0, 1),
        account=account,
        window=rng.integers(0, 40, n),
    )


def test_account_unit_caps_bags_and_groups_rows() -> None:
    fit = _rows()
    win = client_data(fit, 0, "window")
    acc = client_data(fit, 0, "account")
    assert win.units == int((fit.member == 0).sum())  # one unit per row
    counts = np.bincount(acc.unit)
    assert acc.units == len(np.unique(fit.account[fit.member == 0]))
    assert counts.max() <= BAG_CAP and len(acc.y) <= len(win.y)
    again = client_data(fit, 0, "account")
    assert np.array_equal(acc.x, again.x)  # the bag choice is fixed
    with pytest.raises(ValueError):
        client_data(fit, 0, "customer")


def test_dp_hparams_by_regime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import finmesh.training.neural as neural

    path = tmp_path / "dp_hparams.json"
    monkeypatch.setattr(neural, "HPARAMS_PATH", path)
    assert dp_hparams("HI-Medium") == DpHparams()  # no file: A17 defaults
    neural.write_dp_hparams("HI-Small", DpHparams(0.03, 2048, 1e-3, "dp-tune HI-Small"), {"x": 1})
    assert regime("HI-Small") == regime("HI-Medium") == "HI"
    got = dp_hparams("HI-Medium")
    assert (got.clip, got.batch) == (0.03, 2048)
    assert dp_hparams("LI-Medium") == DpHparams()  # another regime stays at defaults
    assert json.loads(path.read_text())["regimes"]["HI"]["evidence"] == {"x": 1}
    from finmesh.training.neural import steps_for

    assert [steps_for(b) for b in (512, 2048, 8192)] == [20, 5, 1]  # same example budget
    assert got.local_steps == 20  # written with the default; read back as given


def _edges(tmp_path: Path) -> Path:
    """A hub (1) with 6 counterparties, a pair (7, 8) and a self-transfer of 9."""
    rows = [(1, c, 10 * c) for c in range(2, 8)] + [(7, 8, 100), (8, 7, 101), (9, 9, 5)]
    frame = pl.DataFrame(
        {
            "src": [r[0] for r in rows],
            "dst": [r[1] for r in rows],
            "timestamp": [r[2] for r in rows],
        },
        schema={"src": pl.UInt64, "dst": pl.UInt64, "timestamp": pl.Int64},
    )
    path = tmp_path / "edges.parquet"
    frame.write_parquet(path)
    return path


def test_degree_cap_keeps_first_counterparties(tmp_path: Path) -> None:
    path = _edges(tmp_path)
    tag, apply = degree_cap(3)
    info = apply(path)
    kept = pl.read_parquet(path)
    assert tag == "cap3" and info["edges_before"] == 9
    hub = kept.filter(pl.col("src") == 1)["dst"].sort().to_list()
    assert hub == [2, 3, 4]  # its first three counterparties in time
    assert kept.filter(pl.col("src") == 7).height == 1  # 7-8 survives: within both caps
    assert kept.filter(pl.col("src") == pl.col("dst")).height == 1  # self-transfer kept
    pairs = (
        pl.concat([kept.select(a="src", b="dst"), kept.select(a="dst", b="src")])
        .filter(pl.col("a") != pl.col("b"))
        .unique()
    )
    assert pairs.group_by("a").len()["len"].max() <= 3  # every account: at most D


def test_remove_accounts_drops_every_leg(tmp_path: Path) -> None:
    path = _edges(tmp_path)
    _, apply = remove_accounts([1, 9], "minus")
    info = apply(path)
    kept = pl.read_parquet(path)
    assert info["edges_after"] == 2 and set(kept["src"].to_list()) == {7, 8}


def test_influence_and_x5_on_the_fixture(
    fixture_paths: object, ingested: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import FeatureStore, build_features
    from finmesh.training.influence import run_influence
    from finmesh.training.x5 import dp_name, run_x5
    from finmesh.training.x5_report import render_x5

    paths = fixture_paths
    run_g0(paths)  # type: ignore[arg-type]
    build_universe(paths, "B8")  # type: ignore[arg-type]
    build_features(paths, "B8")  # type: ignore[arg-type]
    r = run_influence(paths, cap=3, sample=20)  # type: ignore[arg-type]
    member, capped = r["views"]["member"], r["views"]["cap3"]
    assert member["changed_accounts"] > 0
    assert capped["group_size"]["q100"] <= member["group_size"]["q100"]
    # every variant lines up with the labels row for row (slices() checks it)
    assert FeatureStore(paths, "B8", "cap3").meta["variant"]["degree_cap"] == 3  # type: ignore[arg-type]

    tmp = Path(FeatureStore(paths, "B8", "member").layout.root).parent  # type: ignore[arg-type]
    x = run_x5(paths, tmp / "x5test", seeds=(0,), reps=20, cap=3, rounds=3, local_steps=3)  # type: ignore[arg-type]
    s = x["summary"]
    assert {
        dp_name(u, v, e)
        for u in ("window", "account")
        for v in ("member", "cap3")
        for e in (1.0, 3.0, 10.0)
    } <= set(s)
    assert set(s["H2b"]) == {"1", "3", "10"}
    for p in x["per_seed"][0]["privacy"].values():
        for rep in p["clients"].values():
            assert rep["epsilon_spent"] <= rep["target_epsilon"] + 1e-6
    assert "H2b on validation" in render_x5(x)
