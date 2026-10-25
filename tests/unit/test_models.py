"""Week 5: models (label-free), training rows and calibration."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore
from finmesh.eval.universe import build_universe
from finmesh.features.build import FeatureStore, build_features
from finmesh.models.gbdt import GBDT
from finmesh.models.unsupervised import Unsupervised
from finmesh.paths import DatasetPaths
from finmesh.training.baselines import _isotonic, _paired_window, calibration, feature_sets
from finmesh.training.data import NEGATIVE_RATE, training_rows, training_windows

FEATS = ("f0", "f1", "f2")


def _synthetic(n: int, seed: int) -> tuple[pl.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 3)).astype(np.float32)
    y = ((x[:, 0] + 0.5 * x[:, 1] + rng.normal(scale=0.5, size=n)) > 2.2).astype(np.int8)
    x[rng.random(n) < 0.05, 2] = np.nan  # missing values are routed natively
    return pl.DataFrame({f: x[:, i] for i, f in enumerate(FEATS)}), y


def test_gbdt_learns_and_is_deterministic() -> None:
    tr, ytr = _synthetic(6000, 1)
    st, yst = _synthetic(2000, 2)
    te, yte = _synthetic(4000, 3)

    def fit(seed: int) -> GBDT:
        return GBDT(FEATS, seed).fit(
            tr.to_numpy(), ytr, np.ones(len(ytr)), st.to_numpy(), yst, np.ones(len(yst))
        )

    a, b = fit(0), fit(0)
    s = a.score(te)
    assert np.array_equal(s, b.score(te))
    ap, auc = RankedScores(yte, s).stats()
    assert auc > 0.9 and ap > 5 * yte.mean()
    assert a.info["rounds"] >= 1 and set(a.importance()) == set(FEATS)


@pytest.mark.parametrize("kind", ["iforest", "pca"])
def test_unsupervised_scores_outliers_higher(kind: str) -> None:
    rng = np.random.default_rng(0)
    normal = rng.normal(size=(3000, 3))
    normal[:, 1] = normal[:, 0] * 2 + rng.normal(scale=0.1, size=3000)  # correlated pair
    outliers = np.array([[8.0, 16.0, 0.0], [0.0, 9.0, 0.0], [-6.0, 6.0, 5.0]])
    frame = pl.DataFrame({f: normal[:, i] for i, f in enumerate(FEATS)})
    model = Unsupervised(kind, FEATS, 0).fit(frame)
    test = pl.DataFrame({f: np.vstack([normal[:50], outliers])[:, i] for i, f in enumerate(FEATS)})
    s = model.score(test)
    assert s[-3:].min() > np.percentile(s[:50], 90)


def test_isotonic_is_monotone_and_fixes_miscalibration() -> None:
    rng = np.random.default_rng(4)
    p_true = rng.random(20_000) * 0.2
    y = (rng.random(20_000) < p_true).astype(float)
    raw = np.sqrt(p_true)  # monotone but miscalibrated
    f = _isotonic(raw, y)
    cal = f(raw)
    assert np.all(np.diff(f(np.linspace(0, 1, 50))) >= 0)
    assert np.mean((cal - y) ** 2) < np.mean((raw - y) ** 2)


def test_calibration_report_and_paired_window() -> None:
    rng = np.random.default_rng(5)
    n = 4000
    y = (rng.random(n) < 0.05).astype(np.int8)
    score = np.clip(y * 0.3 + rng.random(n) * 0.5, 0, 1)
    frame = pl.DataFrame(
        {
            "member": rng.integers(0, 2, n).astype(np.int32),
            "account": np.arange(n, dtype=np.uint64),
            "window": np.zeros(n, dtype=np.int32),
            "label": y,
            "masked": np.zeros(n, dtype=bool),
            "score": score,
        }
    )
    rep = calibration(frame)
    assert set(rep["calibrators"]) == {"0", "1"}
    assert rep["brier_calibrated_crossfit"] < rep["brier_raw"]
    same = _paired_window(frame, frame, 100, 0)["auprc_difference"]
    assert same["estimate"] == 0.0 and same["low"] == 0.0 and same["high"] == 0.0


def test_training_rows_respect_burn_in_masks_and_sampling(
    fixture_paths: DatasetPaths, ingested: dict[str, object]
) -> None:
    from finmesh.eval.g0 import run_g0

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    store, feats = EvalStore(fixture_paths, "B8"), FeatureStore(fixture_paths, "B8")
    windows = training_windows(store, feats)
    assert windows.burn_in == feats.meta["history_complete_from_window"]
    assert windows.burn_in < windows.stop_from <= windows.train_last
    cols = feature_sets()["all"]
    fit, stop = training_rows(store, feats, cols, windows, seed=0)
    labels = store.partition("train").labels.frame
    usable = labels.filter(~pl.col("masked") & (pl.col("window") >= windows.burn_in))
    assert int(fit.y.sum() + stop.y.sum()) == int(usable["label"].sum())  # every positive kept
    negatives = usable.height - int(usable["label"].sum())
    kept = int((fit.y == 0).sum() + (stop.y == 0).sum())
    assert 0 < kept < negatives
    assert set(np.unique(fit.w[fit.y == 0])) == {1 / NEGATIVE_RATE}
    assert fit.x.shape[1] == len(cols) and fit.x.dtype == np.float32
    # Same seed, same rows.
    fit2, _ = training_rows(store, feats, cols, windows, seed=0)
    assert np.array_equal(np.nan_to_num(fit.x), np.nan_to_num(fit2.x))


def test_baselines_pipeline_and_reports_on_the_fixture(
    fixture_paths: DatasetPaths, ingested: dict[str, object]
) -> None:
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.g1 import gap_summary, render_g1
    from finmesh.training.baselines import run_with_memory
    from finmesh.training.report import render_baselines

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    build_features(fixture_paths, "B8", view="pooled")
    r = run_with_memory(fixture_paths, reps=50, window_reps=20, linked_draws=2)
    assert set(r["results"]) == {
        "random",
        "activity",
        "S0-B",
        "S0-BG",
        "oracle",
        "iforest",
        "pca",
        "S0-BG-noart",
        "oracle-noart",
        "S0-BG+pooled-link",
    }
    assert "self_tx" not in r["importance"]["oracle-noart"]
    assert r["configurations"]["oracle"]["view"] == "pooled"
    assert r["results"]["S0-BG"]["budgets"][0]["linker"] == "local"
    assert r["results"]["oracle"]["budgets"][0]["linker"] == "pooled"
    assert set(r["comparisons"]) == {
        "oracle - S0-BG",
        "S0-BG - S0-B",
        "S0-BG - random",
        "oracle-noart - S0-BG-noart",
    }
    page = render_baselines(r)
    assert "Gate G1 and PT4b comparisons" in page and "Oracle (pooled data" in page
    s = gap_summary(r)
    assert s["dataset"] == fixture_paths.name and "criterion_met" in s
    assert "no HI-Medium baseline artifact yet" in render_g1([s])
