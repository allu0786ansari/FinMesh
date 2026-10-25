"""Week 4: feature extractor correctness, determinism and label independence."""

from __future__ import annotations

import math
import random
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from finmesh.data.splits import window_index_expr
from finmesh.eval.g0 import run_g0
from finmesh.eval.guard import FeatureFrame, LabelLeakError
from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.eval.universe import EvalLayout, build_universe
from finmesh.features import build as build_mod
from finmesh.features.account import DIR_IN, DIR_OUT, account_features
from finmesh.features.build import FeatureStore, build_features, window_partitions
from finmesh.features.edges import chain_rates
from finmesh.features.neighbourhood import NEIGHBOURHOOD_COUNTS, window_features
from finmesh.features.schema import FAMILIES, KEYS, load_schema
from finmesh.paths import DatasetPaths, dataset_paths

# Pinned: changing a released schema file must be a new schema version.
SCHEMA_V1_SHA256 = "240e2915d01e93bc1bccadfd17a6bf6a4b4b6167edda14544abdf40cfbf21a97"
SCHEMA_V2_SHA256 = "c092db8f095773999ba1f8359002b7ed3e9e3591406835ea7026f18f19e658bf"


def test_released_schemas_are_frozen() -> None:
    assert load_schema(1).sha256 == SCHEMA_V1_SHA256, "feature schema v1 changed"
    assert load_schema(2).sha256 == SCHEMA_V2_SHA256, "feature schema v2 changed: release v3"
    v1, v2 = load_schema(1).names, load_schema(2).names
    assert [n for n in v1 if n not in v2] == ["age_windows"]
    assert [n for n in v2 if n not in v1] == ["recency_windows"]


def test_current_schema_is_well_formed() -> None:
    schema = load_schema()
    assert schema.version == 2
    names = schema.names
    assert len(names) == len(set(names))
    assert {f["family"] for f in schema.features} <= set(FAMILIES)
    assert {f["dtype"] for f in schema.features} <= {"u32", "f32"}
    assert set(NEIGHBOURHOOD_COUNTS) == set(schema.family("neighbourhood"))
    assert not set(names) & set(KEYS)


def test_chain_rates_follow_pairs_and_report_unreachable() -> None:
    ratios = pl.DataFrame(
        {
            "payment_currency": ["Euro", "UK Pound", "Yen"],
            "receiving_currency": ["UK Pound", "US Dollar", "Rupee"],
            "ratio": [0.85, 1.3, 0.6],
            "rows": [10, 10, 10],
        }
    )
    rates = chain_rates(["Euro", "Rupee", "UK Pound", "US Dollar", "Yen"], ratios, "US Dollar")
    assert rates["US Dollar"] == 1.0
    assert rates["UK Pound"] == pytest.approx(1.3)
    assert rates["Euro"] == pytest.approx(0.85 * 1.3)
    assert rates["Yen"] is None and rates["Rupee"] is None


def _legs() -> pl.DataFrame:
    t0 = datetime(2022, 9, 1)
    rows = [
        # account 1 at member 0, bank 10; window 0
        (1, 0, 10, 2, 10, 0, DIR_IN, 100.0, 0, False, 0, t0 + timedelta(minutes=10), 0),
        (1, 0, 10, 3, 20, 1, DIR_OUT, 60.0, 0, False, 6, t0 + timedelta(minutes=70), 0),
        (1, 0, 10, 4, 30, None, DIR_OUT, 40.0, 1, True, 3, t0 + timedelta(minutes=130), 0),
        # window 1: one payment to a known counterparty and one self-transfer
        (1, 0, 10, 3, 20, 1, DIR_OUT, 50.0, 0, False, 6, t0 + timedelta(minutes=390), 1),
        (1, 0, 10, 1, 10, 0, DIR_OUT, 5.0, 0, False, 6, t0 + timedelta(minutes=400), 1),
        (1, 0, 10, 1, 10, 0, DIR_IN, 5.0, 0, False, 6, t0 + timedelta(minutes=400), 1),
    ]
    cols = [
        "account",
        "member",
        "bank",
        "cp",
        "cp_bank",
        "cp_member",
        "dir",
        "usd",
        "ccy",
        "xccy",
        "fmt",
        "timestamp",
        "window",
    ]
    return pl.DataFrame(
        rows,
        schema={
            "account": pl.UInt64,
            "member": pl.Int32,
            "bank": pl.Int64,
            "cp": pl.UInt64,
            "cp_bank": pl.Int64,
            "cp_member": pl.Int32,
            "dir": pl.Int8,
            "usd": pl.Float64,
            "ccy": pl.UInt8,
            "xccy": pl.Boolean,
            "fmt": pl.UInt8,
            "timestamp": pl.Datetime("us"),
            "window": pl.Int32,
        },
        orient="row",
    ).select(cols)


def test_account_features_on_a_hand_built_account() -> None:
    f = account_features(_legs()).sort("window")
    w0, w1 = f.row(0, named=True), f.row(1, named=True)

    assert (w0["tx_out"], w0["tx_in"], w0["self_tx"]) == (2, 1, 0)
    assert (w0["fan_out"], w0["fan_in"]) == (2, 1)
    assert (w0["amt_out"], w0["amt_in"], w0["amt_net"]) == (100.0, 100.0, 0.0)
    assert w0["pass_through"] == 1.0
    assert w0["out_amount_hhi"] == pytest.approx(0.6**2 + 0.4**2)
    assert w0["in_amount_hhi"] == pytest.approx(1.0)
    assert w0["in_out_delay_min_h"] == pytest.approx(1.0)
    assert w0["in_out_delay_med_h"] == pytest.approx(1.5)
    assert w0["cross_bank_share"] == pytest.approx(2 / 3)
    assert w0["cross_member_share"] == pytest.approx(1 / 3)
    assert w0["outside_share"] == pytest.approx(1 / 3)
    assert w0["cross_currency_share"] == pytest.approx(1 / 3)
    assert w0["currencies_n"] == 2
    assert w0["fmt_wire_share"] == pytest.approx(1 / 3)
    assert w0["fmt_cheque_share"] == pytest.approx(1 / 3)
    assert (w0["new_cp_n"], w0["new_cp_share"]) == (3, 1.0)
    assert (w0["recency_windows"], w0["prior_active_windows"]) == (13, 0)  # nothing earlier
    assert w0["prior_leg_rate"] == 0.0
    assert w0["legs_vs_history"] == pytest.approx(math.log1p(3))
    assert w0["active_span_h"] == pytest.approx(2.0)

    assert (w1["tx_out"], w1["tx_in"], w1["self_tx"]) == (1, 0, 1)
    assert (w1["new_cp_n"], w1["new_cp_share"]) == (0, 0.0)  # counterparty 3 seen in window 0
    assert (w1["recency_windows"], w1["prior_active_windows"]) == (1, 1)
    assert w1["prior_leg_rate"] == pytest.approx(3 / 12)  # 3 legs over a 12-window span
    assert w1["legs_vs_history"] == pytest.approx(math.log1p(3) - math.log1p(3 / 12))
    assert w1["in_out_delay_min_h"] == pytest.approx(380 / 60)  # self legs ignored
    assert w1["amt_vs_history"] == pytest.approx(math.log1p(60.0) - math.log1p(200.0 / 12))


def test_history_forgets_beyond_the_history_span() -> None:
    legs = _legs()
    late = legs.filter(pl.col("window") == 0).with_columns(
        pl.lit(20, pl.Int32).alias("window"),
        pl.col("timestamp") + timedelta(hours=120),
    )
    f = account_features(pl.concat([legs, late]), history=12).sort("window")
    w20 = f.filter(pl.col("window") == 20).row(0, named=True)
    assert w20["recency_windows"] == 13  # previous activity more than 12 windows back
    assert w20["prior_active_windows"] == 0
    assert w20["prior_leg_rate"] == 0.0
    assert (w20["new_cp_n"], w20["new_cp_share"]) == (3, 1.0)  # forgotten, so new again
    w1 = account_features(pl.concat([legs, late]), history=1).filter(pl.col("window") == 1)
    assert w1["prior_active_windows"][0] == 1 and w1["new_cp_n"][0] == 0


def _brute(edges: set[tuple[int, int]], active: set[int], cap: int) -> dict[int, dict[str, int]]:
    out_n: dict[int, set[int]] = defaultdict(set)
    in_n: dict[int, set[int]] = defaultdict(set)
    for s, d in edges:
        out_n[s].add(d)
        in_n[d].add(s)
    nodes = set(out_n) | set(in_n)
    hub = {n for n in nodes if len(out_n[n]) + len(in_n[n]) > cap}
    res = {}
    for a in active:
        n_out = Counter(c for b in out_n[a] - hub for c in out_n[b] if c != a)
        n_in = Counter(c for d in in_n[a] - hub for c in in_n[d] if c != a)
        res[a] = {
            "nb_out_deg": len(out_n[a]),
            "nb_in_deg": len(in_n[a]),
            "gs_min_fan": min(len(out_n[a]), len(in_n[a])),
            "cyc2": sum(1 for b in out_n[a] if a in out_n[b]),
            "cyc3": sum(1 for b in out_n[a] - hub for c in out_n[b] if c != a and a in out_n[c]),
            "cyc4": sum(
                1
                for b in out_n[a] - hub
                for c in out_n[b]
                if c != a
                for d in out_n[c] - hub
                if d not in (a, b) and a in out_n[d]
            ),
            "sg_out_max": max(n_out.values(), default=0),
            "sg_in_max": max(n_in.values(), default=0),
            "cp_in_deg_max": max((len(in_n[b]) for b in out_n[a]), default=0),
            "cp_out_deg_max": max((len(out_n[b]) for b in in_n[a]), default=0),
            "hub_neighbours": len((out_n[a] | in_n[a]) & hub),
        }
    return res


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_neighbourhood_features_match_brute_force(seed: int) -> None:
    rng = random.Random(seed)
    n, members, lookback, cap = 40, 3, 3, 8
    member_of = {i: rng.randrange(members) for i in range(n)}
    member_of[0] = 0  # node 0 is a hub held at member 0
    rows = []
    for _ in range(260):
        s, d = rng.randrange(n), rng.randrange(n)
        if rng.random() < 0.15:
            s = 0
        if s != d:
            rows.append((s, d, member_of[s], member_of[d], rng.randrange(6)))
    edges = pl.DataFrame(
        rows,
        schema={
            "src": pl.UInt64,
            "dst": pl.UInt64,
            "src_member": pl.Int32,
            "dst_member": pl.Int32,
            "window": pl.Int32,
        },
        orient="row",
    )
    for m in range(members):
        visible = edges.filter((pl.col("src_member") == m) | (pl.col("dst_member") == m))
        for w in range(6):
            got = window_features(visible, m, w, lookback, cap)
            span = [r for r in rows if w - lookback < r[4] <= w and m in (r[2], r[3])]
            active = {r[0] for r in span if r[4] == w and r[2] == m} | {
                r[1] for r in span if r[4] == w and r[3] == m
            }
            want = _brute({(r[0], r[1]) for r in span}, active, cap)
            assert set(got["a"].to_list()) == active
            for row in got.iter_rows(named=True):
                exp = want[row.pop("a")]
                assert row == exp


@pytest.fixture(scope="module")
def built(fixture_paths: DatasetPaths, ingested: dict[str, object]) -> FeatureStore:
    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    return FeatureStore(fixture_paths, "B8")


def test_feature_rows_line_up_with_labels(built: FeatureStore, fixture_paths: DatasetPaths) -> None:
    store = EvalStore(fixture_paths, "B8")
    for part in ("train", "val"):
        labels = store.partition(part).labels.frame
        feats = built.partition(part).frame
        assert feats.select(KEYS).equals(labels.select(KEYS), null_equal=True)
    layout = EvalLayout(fixture_paths, store.window_hours, "B8")
    sealed = pl.read_parquet(layout.partition_dir("test") / "universe_*.parquet")
    assert built.partition("test").frame.select(KEYS).equals(sealed.select(KEYS))


def test_feature_files_follow_the_schema(built: FeatureStore) -> None:
    schema = load_schema()
    frame = built.partition("val").frame
    assert tuple(frame.columns) == (*KEYS, *schema.names)
    for name in schema.names:
        assert frame[name].dtype == schema.dtype(name), name
    floats = [n for n in schema.names if schema.dtype(n) == pl.Float32()]
    assert not frame.select(pl.any_horizontal(pl.col(floats).is_infinite())).to_series().any()
    assert built.meta["currencies"]["rates"]["Euro"] == pytest.approx(1.1)
    assert built.meta["currencies"]["unreachable"] == []


def test_feature_frame_refuses_labels(built: FeatureStore) -> None:
    frame = built.partition("val").frame
    with pytest.raises(LabelLeakError):
        FeatureFrame(frame.with_columns(pl.lit(0).alias("label")))


def _copy_dataset(src: DatasetPaths, root: Path) -> DatasetPaths:
    dst = dataset_paths(src.name, root=root)
    shutil.copytree(src.parquet, dst.parquet, ignore=shutil.ignore_patterns("features_*", "eval_*"))
    return dst


def _all(store: FeatureStore) -> pl.DataFrame:
    return pl.concat([store.partition(p).frame for p in ("train", "val", "test")]).sort(KEYS)


def test_extractor_is_deterministic_and_ignores_labels(
    built: FeatureStore, fixture_paths: DatasetPaths, tmp_path: Path
) -> None:
    reference = _all(built)
    copy = _copy_dataset(fixture_paths, tmp_path)
    tx = pl.read_parquet(copy.transactions)
    flipped = tx.with_columns(pl.col("is_laundering").shuffle(seed=11).alias("is_laundering"))
    assert not flipped["is_laundering"].equals(tx["is_laundering"])
    flipped.write_parquet(copy.transactions)
    build_features(copy, "B8")
    assert _all(FeatureStore(copy, "B8")).equals(reference, null_equal=True)


def test_slicing_does_not_change_features(
    built: FeatureStore,
    fixture_paths: DatasetPaths,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy = _copy_dataset(fixture_paths, tmp_path)
    monkeypatch.setattr(build_mod, "slice_count", lambda paths: 4)
    monkeypatch.setattr(build_mod, "LEGS_PER_SUBSLICE", 500)
    meta = build_features(copy, "B8")
    assert meta["slices"] == 4 and meta["subslices"] > 1
    assert _all(FeatureStore(copy, "B8")).equals(_all(built), null_equal=True)


def test_window_partitions_match_transaction_partitions(fixture_paths: DatasetPaths) -> None:
    plan = load_plan(fixture_paths)
    parts = window_partitions(plan)
    from finmesh.data.splits import partition_expr

    seen = (
        pl.scan_parquet(fixture_paths.transactions)
        .select(window_index_expr(plan).alias("w"), partition_expr(plan).cast(pl.String).alias("p"))
        .drop_nulls("w")
        .unique()
        .collect()
    )
    for w, p in seen.iter_rows():
        assert parts[w] == p


def test_schema_document_matches_schema_file() -> None:
    from finmesh.features.schema import render_schema
    from finmesh.paths import REPO_ROOT

    for version in (1, 2):
        doc = REPO_ROOT / "docs" / "protocol" / f"features_v{version}.md"
        assert doc.read_text() == render_schema(load_schema(version)), f"regenerate {doc.name}"


def test_psi_is_zero_for_identical_and_large_for_shifted() -> None:
    import numpy as np

    from finmesh.features.drift import psi

    rng = np.random.default_rng(0)
    x = rng.normal(size=20_000)
    assert psi(x, x) == pytest.approx(0.0, abs=1e-9)
    assert psi(x, x + 1.0) > 0.25
    with_missing = np.where(rng.random(20_000) < 0.3, np.nan, x)
    assert psi(x, with_missing) > 0.25  # missing values are their own bin


def test_diagnostics_on_the_fixture(built: FeatureStore, fixture_paths: DatasetPaths) -> None:
    from finmesh.eval.diagnostics import pattern_visibility, positive_profile
    from finmesh.features.drift import feature_drift

    store = EvalStore(fixture_paths, "B8")
    profile = positive_profile(fixture_paths, store)
    val = store.partition("val").labels.frame.filter(~pl.col("masked"))
    assert profile["val"]["positives"] == int(val["label"].sum())
    assert profile["val"]["incidental"] == 0  # fixture accounts are never busy hubs

    membership = pl.read_parquet(fixture_paths.parquet / "membership_B8.parquet")
    vis = {
        r["pattern"]: r for r in pattern_visibility(fixture_paths, built, membership)["patterns"]
    }
    # An account's own legs are always visible to its member: fan patterns always fire.
    assert vis["FAN-OUT"]["fired"] == 1.0 and vis["FAN-IN"]["fired"] == 1.0
    assert "fired" not in vis["RANDOM"]

    drift = {r["feature"]: r for r in feature_drift(built)}
    assert set(drift) == set(built.schema.names)
    assert drift["recency_windows"]["psi"] < 0.25  # stationary after the burn-in
