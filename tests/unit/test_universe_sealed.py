from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from finmesh.data import lowmem
from finmesh.data.splits import partition_expr, window_index_expr
from finmesh.eval.g0 import run_g0
from finmesh.eval.guard import FeatureFrame, LabelLeakError, ScoreFrame
from finmesh.eval.harness import harness_check, random_scorer
from finmesh.eval.sealed import EvalStore, SealedTestError, open_sealed_test, read_access_log
from finmesh.eval.split_io import load_plan
from finmesh.eval.universe import build_universe
from finmesh.paths import DatasetPaths


@pytest.fixture(scope="module")
def store(fixture_paths: DatasetPaths, ingested: dict[str, object]) -> EvalStore:
    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    return EvalStore(fixture_paths, "B8")


def _naive_universe(paths: DatasetPaths) -> pl.DataFrame:
    """Independent, eager recomputation of the labels from raw tables."""
    plan = load_plan(paths)
    tx = pl.read_parquet(paths.transactions).with_columns(
        partition_expr(plan).cast(pl.String).alias("partition"),
        window_index_expr(plan).alias("window"),
    )
    assign = pl.read_parquet(paths.parquet / "scheme_assignment_w6.parquet").select(
        "scheme_id", pl.col("partition").cast(pl.String).alias("sp")
    )
    links = pl.read_parquet(paths.scheme_links).join(assign, on="scheme_id")
    tx = tx.join(links.select("tx_id", "sp"), on="tx_id", how="left").filter(
        pl.col("partition").is_in(["train", "val", "test"])
    )
    tx = tx.with_columns(
        (pl.col("sp").is_not_null() & (pl.col("sp") != pl.col("partition"))).alias("m"),
    )
    sides = pl.concat(
        [
            tx.select(pl.col("src_key").alias("key"), "window", "partition", "is_laundering", "m"),
            tx.select(pl.col("dst_key").alias("key"), "window", "partition", "is_laundering", "m"),
        ]
    )
    return (
        sides.group_by("key", "window", "partition")
        .agg(
            ((pl.col("is_laundering") == 1) & ~pl.col("m")).any().alias("pos"),
            ((pl.col("is_laundering") == 1) & pl.col("m")).any().alias("mb"),
        )
        .with_columns(
            pl.col("key").hash(seed=0).alias("account"),
            pl.col("window").cast(pl.Int32),
            (pl.col("mb") & ~pl.col("pos")).alias("masked"),
            pl.col("pos").cast(pl.Int8).alias("label"),
        )
    )


def test_universe_matches_naive_recomputation(
    store: EvalStore, fixture_paths: DatasetPaths
) -> None:
    naive = _naive_universe(fixture_paths)
    for part in ("train", "val"):
        got = store.partition(part).labels.frame.select("account", "window", "label", "masked")
        want = naive.filter(pl.col("partition") == part).select(
            "account", "window", "label", "masked"
        )
        assert got.sort("account", "window").equals(want.sort("account", "window"))


def test_slicing_does_not_change_labels(
    fixture_paths: DatasetPaths, store: EvalStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = store.partition("val").labels.frame.sort("account", "window")
    monkeypatch.setattr(lowmem, "KEYS_PER_SLICE", 900)
    meta = build_universe(fixture_paths, "B8")
    assert meta["slices"] > 5
    after = EvalStore(fixture_paths, "B8").partition("val").labels.frame.sort("account", "window")
    assert before.equals(after)


def test_scheme_windows_are_positive_universe_rows(store: EvalStore) -> None:
    for part in ("train", "val"):
        data = store.partition(part)
        joined = data.scheme_windows.join(
            data.labels.frame, on=["member", "account", "window"], how="left"
        )
        assert joined["label"].null_count() == 0
        assert (joined["label"] == 1).all()
        assert set(data.schemes["scheme_id"]) == set(data.scheme_windows["scheme_id"]) | set(
            data.schemes.filter(pl.col("member_accounts") == 0)["scheme_id"]
        )


def test_store_refuses_test_and_seal_logs(store: EvalStore) -> None:
    with pytest.raises(SealedTestError):
        store.partition("test")
    with pytest.raises(SealedTestError):
        store.universe_keys("test")
    assert read_access_log(store.paths) == []
    config = {"model": "unit-test", "budgets": ["fpr_0.001"]}
    test = open_sealed_test(store, config, seed=1, purpose="unit test")
    assert test.partition == "test" and test.labels.frame.height > 0
    log = read_access_log(store.paths)
    assert len(log) == 1 and log[0]["seed"] == 1 and log[0]["repeat"] is False
    with pytest.raises(SealedTestError):
        open_sealed_test(store, config, seed=1, purpose="again")
    assert len(read_access_log(store.paths)) == 1  # a refused opening is not logged as access
    open_sealed_test(store, config, seed=1, purpose="deliberate repeat", allow_repeat=True)
    open_sealed_test(store, config, seed=2, purpose="second seed")
    log = read_access_log(store.paths)
    assert [e["repeat"] for e in log] == [False, True, False]


def test_label_guard_types() -> None:
    keys = {"member": [0], "account": [1], "window": [3]}
    FeatureFrame(pl.DataFrame({**keys, "fan_out": [2]}))
    for col in ("label", "is_laundering", "scheme_id", "masked", "laundering_score"):
        with pytest.raises(LabelLeakError):
            FeatureFrame(pl.DataFrame({**keys, col: [1]}))
    with pytest.raises(LabelLeakError):
        ScoreFrame(pl.DataFrame({**keys, "score": [0.1], "label": [1]}))
    with pytest.raises(ValueError):
        ScoreFrame(pl.DataFrame({**keys}))


def test_harness_check_runs_and_random_is_calibrated(store: EvalStore) -> None:
    result = harness_check(store, reps=200)
    rnd = result["scorers"]["random"]
    assert rnd["unscored_account_windows"] == 0
    assert 0.2 < rnd["window"]["auroc"]["estimate"] < 0.8  # tiny fixture: wide, but not signal
    keys = store.universe_keys("val")
    a = random_scorer(keys, 0).frame["score"]
    b = random_scorer(keys, 0).frame["score"]
    assert a.equals(b) and a.min() >= 0.0 and a.max() < 1.0  # deterministic, in [0, 1)
    for budget in rnd["budgets"]:
        assert budget["linked"]["estimate"] == 0.0  # no fusion yet


def test_fast_score_join_equals_hash_join(store: EvalStore) -> None:
    labels = store.partition("val").labels
    scores = random_scorer(labels.keys(), 3)
    fast = labels.join_scores(scores)
    shuffled = ScoreFrame(scores.frame.sample(fraction=1.0, shuffle=True, seed=1))
    slow = labels.join_scores(shuffled)  # row order differs: falls back to the hash join
    key = ["member", "account", "window"]
    assert fast.sort(key).equals(slow.sort(key))
    assert fast["score"].null_count() == 0
    assert "label" not in labels.keys().columns


def test_incidental_positives_are_masked_in_primary_and_positive_in_touch(
    fixture_paths: DatasetPaths, store: EvalStore, tmp_path: Path
) -> None:
    """A busy account that one scheme leg passes through (A9)."""
    import shutil

    from finmesh.data.lowmem import hashed_key
    from finmesh.data.splits import window_index_expr
    from finmesh.eval.split_io import load_plan
    from finmesh.paths import dataset_paths

    copy = dataset_paths(fixture_paths.name, root=tmp_path)
    shutil.copytree(fixture_paths.parquet, copy.parquet, ignore=shutil.ignore_patterns("eval_*"))
    tx = pl.read_parquet(copy.transactions)
    plan = load_plan(copy)
    val = plan.period("val")
    bad = tx.filter(
        (pl.col("is_laundering") == 1)
        & (pl.col("timestamp") >= val.start)
        & (pl.col("timestamp") < val.end)
    ).row(0, named=True)
    senders = tx.filter(pl.col("dst_key") != bad["dst_key"])["src_key"].unique().head(30)
    extra = pl.DataFrame(
        [
            {**bad, "tx_id": int(tx["tx_id"].max()) + 1 + k, "is_laundering": 0, "src_key": s}
            for k, s in enumerate(senders.to_list())
        ],
        schema=tx.schema,
    )
    pl.concat([tx, extra]).write_parquet(copy.transactions)
    build_universe(copy, "B8")
    st = EvalStore(copy, "B8")

    key = pl.DataFrame({"account": [bad["dst_key"]], "timestamp": [bad["timestamp"]]}).select(
        hashed_key("account").alias("account"), window_index_expr(plan).alias("window")
    )
    primary = st.partition("val").labels.frame.join(key, on=["account", "window"])
    touch = st.partition("val", variant="touch").labels.frame.join(key, on=["account", "window"])
    assert primary.row(0, named=True)["incidental"]
    assert (primary["label"][0], primary["masked"][0]) == (0, True)
    assert (touch["label"][0], touch["masked"][0]) == (1, False)
    p_sw = st.partition("val").scheme_windows.join(key, on=["account", "window"])
    assert p_sw.height == 0  # the primary label never counts it towards scheme detection
    assert st.meta["counts"]["val"]["incidental"] == 1
