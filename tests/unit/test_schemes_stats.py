"""Scheme metrics on a hand-built federation with known answers, and the statistics."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from finmesh.eval.metrics import RankedScores, average_precision
from finmesh.eval.schemes import random_detection_probability, scheme_outcomes
from finmesh.eval.stats import holm, interval_from, paired_difference, scheme_rate_ci

KEY_SCHEMA = {"member": pl.Int32, "account": pl.UInt64, "window": pl.Int32}

# Scheme 1: accounts a (member 0, window 10), b (member 1, window 11), c (member 1, window 14).
# Scheme 2: account d (member 0, window 12).
SCHEME_WINDOWS = pl.DataFrame(
    {
        "scheme_id": [1, 1, 1, 2],
        "member": [0, 1, 1, 0],
        "account": [1, 2, 3, 4],
        "window": [10, 11, 14, 12],
    },
    schema={"scheme_id": pl.Int64, **KEY_SCHEMA},
)
SCHEMES = pl.DataFrame(
    {
        "scheme_id": [1, 2],
        "pattern": ["CYCLE", "FAN-IN"],
        "members": [2, 1],
        "first_window": [10, 12],
    },
    schema={
        "scheme_id": pl.Int64,
        "pattern": pl.String,
        "members": pl.UInt32,
        "first_window": pl.Int32,
    },
)


def _alerts(alerted: set[tuple[int, int]]) -> pl.DataFrame:
    rows = SCHEME_WINDOWS.select("member", "account", "window")
    extra = pl.DataFrame({"member": [0], "account": [99], "window": [10]}, schema=KEY_SCHEMA)
    rows = pl.concat([rows, extra])
    return rows.with_columns(
        pl.struct("account", "window")
        .map_elements(lambda r: (r["account"], r["window"]) in alerted, return_dtype=pl.Boolean)
        .alias("alert")
    )


def test_detection_and_time_to_detect() -> None:
    out = scheme_outcomes(_alerts({(2, 11)}), SCHEME_WINDOWS, SCHEMES, window_hours=6)
    rows = {r["scheme_id"]: r for r in out.to_dicts()}
    assert rows[1]["detected"] is True and rows[1]["time_to_detect_h"] == 6.0
    assert rows[2]["detected"] is False and rows[2]["time_to_detect_h"] is None
    assert not out["linked"].any()  # no incidents: every alert stands alone


def test_delay_limits_what_counts() -> None:
    out = scheme_outcomes(
        _alerts({(2, 11)}), SCHEME_WINDOWS, SCHEMES, window_hours=6, delay_windows=0
    )
    assert out.filter(pl.col("scheme_id") == 1)["detected"].item() is False


def test_linked_needs_two_accounts_in_one_incident() -> None:
    alerts = _alerts({(1, 10), (2, 11), (99, 10)})
    same = pl.DataFrame(
        {"member": [0, 1, 0], "account": [1, 2, 99], "window": [10, 11, 10], "incident": [7, 7, 8]},
        schema={**KEY_SCHEMA, "incident": pl.Int64},
    )
    out = scheme_outcomes(alerts, SCHEME_WINDOWS, SCHEMES, 6, incidents=same)
    s1 = out.filter(pl.col("scheme_id") == 1).row(0, named=True)
    assert s1["linked"] and s1["linked_cross_member"]
    split = same.with_columns(pl.Series("incident", [7, 9, 8]))
    out = scheme_outcomes(alerts, SCHEME_WINDOWS, SCHEMES, 6, incidents=split)
    assert not out.filter(pl.col("scheme_id") == 1)["linked"].item()


def test_random_detection_probability_exact() -> None:
    rates = pl.DataFrame(
        {"member": [0, 1], "rate": [0.1, 0.2]}, schema={"member": pl.Int32, "rate": pl.Float64}
    )
    p = random_detection_probability(SCHEME_WINDOWS, SCHEMES, rates).sort("scheme_id")
    assert p["p_detect"].to_list() == pytest.approx([1 - 0.9 * 0.8 * 0.8, 0.1])
    p0 = random_detection_probability(SCHEME_WINDOWS, SCHEMES, rates, delay_windows=1).sort(
        "scheme_id"
    )
    assert p0["p_detect"].to_list() == pytest.approx([1 - 0.9 * 0.8, 0.1])


def test_holm_known_values() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5]) == [0.5]


def test_scheme_rate_ci_and_seed_averaging() -> None:
    x = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 1])
    ci = scheme_rate_ci(x, reps=2000, seed=1)
    assert ci.estimate == pytest.approx(0.7)
    assert ci.low < 0.7 < ci.high
    two_seeds = np.stack([x, 1 - x], axis=1)
    assert scheme_rate_ci(two_seeds, reps=10).estimate == pytest.approx(0.5)


def test_paired_difference_detects_a_real_gain() -> None:
    rng = np.random.default_rng(0)
    b = (rng.random(300) < 0.3).astype(float)
    a = np.maximum(b, (rng.random(300) < 0.3).astype(float))
    interval, p = paired_difference(a, b, reps=2000)
    assert interval.low > 0 and p < 0.01
    same, p_same = paired_difference(b, b, reps=500)
    assert same.estimate == 0.0 and p_same == 1.0


def test_ranked_bootstrap_estimate_and_interval() -> None:
    rng = np.random.default_rng(2)
    y = (rng.random(2000) < 0.05).astype(float)
    s = rng.random(2000) + y
    clusters = rng.integers(0, 300, 2000)
    ranked = RankedScores(y, s)
    ap_reps, _auc_reps = ranked.bootstrap(clusters, reps=200, seed=0)
    ci = interval_from(ap_reps, ranked.average_precision())
    assert ci.estimate == pytest.approx(average_precision(y, s))
    assert ci.low <= ci.estimate <= ci.high
    # A replicate equals the plain metric with the same weights, rebuilt independently.
    _, inverse = np.unique(clusters, return_inverse=True)
    w = np.random.default_rng(0).poisson(1.0, size=inverse.max() + 1).astype(float)[inverse]
    assert ap_reps[0] == pytest.approx(average_precision(y, s, w))
