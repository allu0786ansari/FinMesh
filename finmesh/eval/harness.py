"""Evaluate scores on one partition: the single entry point every experiment uses.

``evaluate`` takes label-free scores (:class:`ScoreFrame`), joins the
partition's labels, and returns window-level metrics with intervals, and for
each alert budget: alert volumes, precision, false alerts per 1,000 accounts
per day, scheme detection and linked detection with intervals, time to detect,
and the exact random-alert baseline at the same per-member alert rates.

``harness_check`` is the week-3 self-test on real data: two label-free
reference scorers (random, and transaction count) are scored on validation
with thresholds fitted on train. The random scorer must land on its analytic
baseline (AUPRC about the prevalence, AUROC about 0.5, detection inside the
random-alert interval); if it does not, the harness is wrong.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import polars as pl

from finmesh.eval.budgets import DEFAULT_BUDGETS, Budget, apply_budget, fit_thresholds
from finmesh.eval.guard import KEY_COLUMNS, ScoreFrame
from finmesh.eval.metrics import RankedScores, precision_at_k
from finmesh.eval.schemes import alert_rates, random_detection_probability, scheme_outcomes
from finmesh.eval.sealed import EvalStore, PartitionData
from finmesh.eval.stats import interval_from, scheme_rate_ci

UNSCORED = -1e300  # windows a detector did not score rank below everything


def _num(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _scored_with_labels(part: PartitionData, scores: ScoreFrame) -> tuple[pl.DataFrame, int]:
    joined = part.labels.join_scores(scores)
    unscored = int(joined["score"].null_count())
    return joined.with_columns(pl.col("score").fill_null(UNSCORED).cast(pl.Float64)), unscored


def window_metrics(joined: pl.DataFrame, reps: int, seed: int) -> dict[str, Any]:
    ev = joined.filter(~pl.col("masked"))
    y = ev["label"].to_numpy()
    s = ev["score"].to_numpy()
    accounts = ev["account"].to_numpy()
    positives = int(y.sum())
    out: dict[str, Any] = {
        "account_windows": ev.height,
        "positives": positives,
        "prevalence": positives / ev.height if ev.height else None,
    }
    if positives == 0 or positives == ev.height:
        out.update({"auprc": None, "auroc": None})
        return out
    ranked = RankedScores(y, s)
    ap, auc = ranked.stats()
    ap_reps, auc_reps = ranked.bootstrap(accounts, reps, seed)
    out["auprc"] = interval_from(ap_reps, ap).to_dict()
    out["auroc"] = interval_from(auc_reps, auc).to_dict()
    for k in (100, 1000):
        out[f"precision_at_{k}"] = precision_at_k(y, s, k)
    return out


def budget_metrics(
    joined: pl.DataFrame,
    part: PartitionData,
    budget: Budget,
    *,
    thresholds: pl.DataFrame | None,
    accounts_per_member: pl.DataFrame,
    window_hours: int,
    delay_windows: int | None,
    incidents: pl.DataFrame | None,
    reps: int,
    seed: int,
) -> tuple[dict[str, Any], pl.DataFrame]:
    alerts = apply_budget(
        joined.select(*KEY_COLUMNS, "score", "label", "masked"),
        budget,
        thresholds=thresholds,
        accounts_per_member=accounts_per_member,
        window_hours=window_hours,
    )
    unmasked = alerts.filter(~pl.col("masked"))
    n_alerts = int(alerts["alert"].sum())
    tp = int(unmasked.filter(pl.col("alert") & (pl.col("label") == 1)).height)
    fp = int(unmasked.filter(pl.col("alert") & (pl.col("label") == 0)).height)
    positives = int(unmasked["label"].sum())
    negatives = unmasked.height - positives
    total_accounts = float(accounts_per_member["accounts"].sum())
    member_fpr = (
        unmasked.filter(pl.col("label") == 0)
        .group_by("member")
        .agg(pl.col("alert").mean().alias("fpr"))
    )
    outcomes = scheme_outcomes(
        alerts, part.scheme_windows, part.schemes, window_hours, delay_windows, incidents
    )
    rates = alert_rates(alerts)
    random_p = random_detection_probability(part.scheme_windows, part.schemes, rates, delay_windows)
    detected = outcomes["detected"].to_numpy()
    random_rate = _num(random_p["p_detect"].mean()) if random_p.height else None
    # Interval of the random baseline: Bernoulli draws per scheme, resampled.
    rng = np.random.default_rng(seed)
    p = random_p["p_detect"].to_numpy()
    draws = (rng.random((reps, len(p))) < p).mean(axis=1) if len(p) else np.array([np.nan])
    ttd = outcomes.filter(pl.col("detected"))["time_to_detect_h"]
    result = {
        "budget": budget.name,
        "alerts": n_alerts,
        "alerts_per_1000_accounts_per_day": n_alerts / (total_accounts / 1000) / part.days,
        "false_alerts_per_1000_accounts_per_day": fp / (total_accounts / 1000) / part.days,
        "precision": tp / (tp + fp) if tp + fp else None,
        "window_recall": tp / positives if positives else None,
        "fpr": fp / negatives if negatives else None,
        "max_member_fpr": _num(member_fpr["fpr"].max()) if member_fpr.height else None,
        "schemes": outcomes.height,
        "detected": scheme_rate_ci(detected, reps, seed).to_dict() if outcomes.height else None,
        "linked": scheme_rate_ci(outcomes["linked"].to_numpy(), reps, seed).to_dict()
        if outcomes.height
        else None,
        "linked_cross_member": scheme_rate_ci(
            outcomes["linked_cross_member"].to_numpy(), reps, seed
        ).to_dict()
        if outcomes.height
        else None,
        "random_alert_detected": {
            "estimate": random_rate,
            "low": float(np.nanpercentile(draws, 2.5)),
            "high": float(np.nanpercentile(draws, 97.5)),
        },
        "median_time_to_detect_h": _num(ttd.median()) if ttd.len() else None,
        "delay_windows": delay_windows,
    }
    return result, outcomes


def evaluate(
    part: PartitionData,
    scores: ScoreFrame,
    *,
    accounts_per_member: pl.DataFrame,
    window_hours: int,
    thresholds: dict[str, pl.DataFrame],
    budgets: tuple[Budget, ...] = DEFAULT_BUDGETS,
    delay_windows: int | None = None,
    incidents: pl.DataFrame | None = None,
    reps: int = 1000,
    window_reps: int = 200,
    seed: int = 0,
) -> dict[str, Any]:
    joined, unscored = _scored_with_labels(part, scores)
    report: dict[str, Any] = {
        "partition": part.partition,
        "hours": part.hours,
        "unscored_account_windows": unscored,
        "window": window_metrics(joined, window_reps, seed),
        "budgets": [],
    }
    for budget in budgets:
        result, _ = budget_metrics(
            joined,
            part,
            budget,
            thresholds=thresholds.get(budget.name),
            accounts_per_member=accounts_per_member,
            window_hours=window_hours,
            delay_windows=delay_windows,
            incidents=incidents,
            reps=reps,
            seed=seed,
        )
        report["budgets"].append(result)
    return report


def fit_all_thresholds(
    part: PartitionData, scores: ScoreFrame, budgets: tuple[Budget, ...] = DEFAULT_BUDGETS
) -> dict[str, pl.DataFrame]:
    """Fit fpr thresholds on an earlier partition (train for val, val for test)."""
    joined, _ = _scored_with_labels(part, scores)
    needed = joined.select("member", "account", "window", "score", "label", "masked")
    return {b.name: fit_thresholds(needed, b) for b in budgets if b.kind == "fpr"}


# ---------------------------------------------------------------- reference scorers
Scorer = Callable[[pl.DataFrame, int], ScoreFrame]


def random_scorer(keys: pl.DataFrame, seed: int) -> ScoreFrame:
    """Uniform scores, a deterministic function of (account, window, seed)."""
    score = (pl.struct("account", "window").hash(seed=seed).cast(pl.Float64) / float(2**64)).alias(
        "score"
    )
    return ScoreFrame(keys.select(*KEY_COLUMNS, score))


def activity_scorer(keys: pl.DataFrame, seed: int) -> ScoreFrame:
    """Number of transaction legs in the window: a label-free, weak signal."""
    del seed
    return ScoreFrame(keys.select(*KEY_COLUMNS, pl.col("tx").cast(pl.Float64).alias("score")))


REFERENCE_SCORERS: dict[str, Scorer] = {"random": random_scorer, "activity": activity_scorer}


def harness_check(store: EvalStore, seed: int = 0, reps: int = 1000) -> dict[str, Any]:
    train = store.partition("train")
    val = store.partition("val")
    apm = store.accounts_per_member()
    out: dict[str, Any] = {
        "dataset": store.paths.name,
        "option": store.meta["option"],
        "window_hours": store.window_hours,
        "fit_on": "train",
        "evaluated_on": "val",
        "scorers": {},
    }
    train_keys = train.labels.keys()
    val_keys = val.labels.keys()
    for name, scorer in REFERENCE_SCORERS.items():
        thresholds = fit_all_thresholds(train, scorer(train_keys, seed))
        out["scorers"][name] = evaluate(
            val,
            scorer(val_keys, seed),
            accounts_per_member=apm,
            window_hours=store.window_hours,
            thresholds=thresholds,
            reps=reps,
            seed=seed,
        )
    return out
