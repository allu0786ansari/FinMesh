from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from finmesh.eval.budgets import Budget, apply_budget, fit_thresholds
from finmesh.eval.metrics import average_precision, precision_at_k, roc_auc


def _auroc_bruteforce(y: np.ndarray, s: np.ndarray) -> float:
    pos, neg = s[y == 1], s[y == 0]
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins / (len(pos) * len(neg)))


def test_average_precision_known_value() -> None:
    y = np.array([1, 0, 1, 0])
    s = np.array([0.9, 0.8, 0.7, 0.1])
    assert average_precision(y, s) == pytest.approx(0.5 * 1 + 0.5 * (2 / 3))


def test_ties_are_one_threshold() -> None:
    y = np.array([1, 0])
    s = np.array([0.5, 0.5])
    assert average_precision(y, s) == pytest.approx(0.5)
    assert roc_auc(y, s) == pytest.approx(0.5)
    # Storage order of tied rows must not matter.
    assert average_precision(y[::-1], s[::-1]) == pytest.approx(0.5)


def test_auroc_matches_mann_whitney_with_ties() -> None:
    rng = np.random.default_rng(3)
    y = (rng.random(500) < 0.1).astype(int)
    s = rng.integers(0, 20, 500).astype(float) + 2 * y  # many ties, some signal
    assert roc_auc(y, s) == pytest.approx(_auroc_bruteforce(y, s), abs=1e-12)


def test_weights_equal_duplication() -> None:
    rng = np.random.default_rng(4)
    y = (rng.random(200) < 0.2).astype(int)
    s = rng.random(200)
    w = rng.integers(0, 3, 200).astype(float)
    dup = np.repeat(np.arange(200), w.astype(int))
    assert average_precision(y, s, w) == pytest.approx(average_precision(y[dup], s[dup]))
    assert roc_auc(y, s, w) == pytest.approx(roc_auc(y[dup], s[dup]))


def test_extremes_and_errors() -> None:
    y = np.array([0, 0, 1, 1])
    assert roc_auc(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert roc_auc(y, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0
    assert np.isnan(average_precision(np.zeros(3), np.arange(3.0)))
    with pytest.raises(ValueError):
        roc_auc(y, np.array([0.1, np.nan, 0.3, 0.4]))


def test_precision_at_k_averages_ties_at_cut() -> None:
    y = np.array([1, 0, 1, 0])
    s = np.array([0.9, 0.5, 0.5, 0.1])
    assert precision_at_k(y, s, 1) == 1.0
    assert precision_at_k(y, s, 2) == pytest.approx((1 + 0.5) / 2)


def _scored() -> pl.DataFrame:
    rng = np.random.default_rng(5)
    n = 20_000
    return pl.DataFrame(
        {
            "member": rng.integers(0, 2, n).astype(np.int32),
            "account": rng.integers(0, 5_000, n).astype(np.uint64),
            "window": rng.integers(0, 10, n).astype(np.int32),
            "score": rng.random(n),
            "label": (rng.random(n) < 0.01).astype(np.int8),
            "masked": np.zeros(n, dtype=bool),
        }
    )


def test_fpr_budget_is_respected_per_member() -> None:
    df = _scored()
    budget = Budget("fpr", 0.01)
    th = fit_thresholds(df, budget)
    alerts = apply_budget(df, budget, thresholds=th)
    neg = alerts.filter(pl.col("label") == 0)
    per_member = neg.group_by("member").agg(pl.col("alert").mean())["alert"]
    assert (per_member <= 0.01).all()
    assert (per_member > 0.008).all()  # close to the budget, not far below it


def test_fpr_budget_with_heavy_ties_still_alerts() -> None:
    # Integer scores: most windows tie at 1. A strict "> threshold" would alert nothing.
    df = _scored().with_columns((pl.col("score") * 3).floor().clip(0, 1))
    budget = Budget("fpr", 0.01)
    alerts = apply_budget(df, budget, thresholds=fit_thresholds(df, budget))
    neg = alerts.filter(pl.col("label") == 0)
    rates = neg.group_by("member").agg(pl.col("alert").mean())["alert"]
    assert ((rates > 0.009) & (rates <= 0.01)).all()


def test_fpr_budget_needs_thresholds() -> None:
    with pytest.raises(ValueError):
        apply_budget(_scored(), Budget("fpr", 0.01))
    with pytest.raises(ValueError):
        fit_thresholds(_scored(), Budget("per_1000_per_day", 1))


def test_per_day_budget_top_k_per_member_window() -> None:
    df = pl.DataFrame(
        {
            "member": [0, 0, 0, 0, 1, 1],
            "account": [1, 2, 3, 4, 5, 6],
            "window": [0, 0, 0, 1, 0, 0],
            "score": [0.9, 0.9, 0.1, 0.5, 0.3, 0.2],
        },
        schema={"member": pl.Int32, "account": pl.UInt64, "window": pl.Int32, "score": pl.Float64},
    )
    accounts = pl.DataFrame(
        {"member": [0, 1], "accounts": [4000, 4000]},
        schema={"member": pl.Int32, "accounts": pl.UInt32},
    )
    # 1 per 1000 per day x 4000 accounts x 6/24 day = 1 alert per member per window.
    out = apply_budget(
        df, Budget("per_1000_per_day", 1.0), accounts_per_member=accounts, window_hours=6
    ).sort("account")
    assert out["alert"].to_list() == [True, False, False, True, True, False]  # tie -> lower account


def _ap_reference(y: np.ndarray, s: np.ndarray, w: np.ndarray) -> float:
    """Straightforward AP over distinct thresholds (independent of RankedScores)."""
    total_pos = float((y * w).sum())
    ap, prev_recall = 0.0, 0.0
    for t in np.unique(s)[::-1]:
        sel = s >= t
        tp = float((y * w)[sel].sum())
        fp = float(((1 - y) * w)[sel].sum())
        recall = tp / total_pos
        if tp + fp > 0:
            ap += (recall - prev_recall) * tp / (tp + fp)
        prev_recall = recall
    return ap


def test_fast_ap_matches_reference_with_ties_and_weights() -> None:
    rng = np.random.default_rng(11)
    y = (rng.random(3000) < 0.03).astype(float)
    s = rng.integers(0, 40, 3000).astype(float) + 3 * y
    w = rng.poisson(1.0, 3000).astype(float)
    assert average_precision(y, s, w) == pytest.approx(_ap_reference(y, s, w), rel=1e-12)
    assert average_precision(y, s) == pytest.approx(_ap_reference(y, s, np.ones(3000)), rel=1e-12)
