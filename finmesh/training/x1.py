"""Experiment X1 on validation: the sharing ladder (week 7; amendment A13).

Per seed, every member runs its S0 detector (local LightGBM, calibrated on
the held-out end of training) and builds evidence records for its
candidates: account-windows with calibrated probability at the evidence
floor, or alerted. Then for each sharing level:

1. **Protocol.** Every candidate asks about its counterparties at other
   members (``finmesh.sharing.simulate``); responders answer at the level.
2. **Triage (fusion).** Each member re-scores its candidates from what it
   received and what it was asked (``finmesh.fusion.triage``). The
   **primary rule is the stacker**: a per-member logistic regression on the
   evidence features, fitted on one half of the validation windows and
   applied to the other (two-fold, by time). Noisy-OR and k-of-n are fixed
   secondary rules. Each member cuts its queue at its own budget.
3. **Linking.** Final alerts at different members are linked when the
   accounts transacted within the lookback; at S1 and above, alert flags
   travel through tokens (week 6 showed the protocol links exactly these
   pairs). S0 links only within a member.

Also: the oracle (pooled data and graph, pooled linking), a plaintext
score-propagation baseline (no cryptography), and the random-alert baseline.
Per-scheme outcomes are averaged over seeds before the scheme bootstrap.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from finmesh.eval.budgets import apply_budget
from finmesh.eval.guard import KEY_COLUMNS, ScoreFrame
from finmesh.eval.harness import evaluate, random_scorer
from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore, PartitionData
from finmesh.eval.split_io import load_plan
from finmesh.eval.stats import interval_from, paired_difference, scheme_rate_ci
from finmesh.features.build import FeatureStore
from finmesh.fusion.local import Linker, link_edges
from finmesh.fusion.triage import evidence_features, feature_names, k_of_n, noisy_or
from finmesh.models.autoencoder import Autoencoder
from finmesh.models.gbdt import GBDT
from finmesh.paths import DatasetPaths
from finmesh.sharing.evidence import bucket, build_records, load_evidence_schema
from finmesh.sharing.simulate import counterparty_requests, simulate
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import (
    DELAY_WINDOWS,
    PRIMARY,
    _per_member,
    feature_sets,
    fit_local_models,
    score_rows,
)
from finmesh.training.data import sample_rows, slices, training_rows, training_windows
from finmesh.training.sharing_run import _calibrators, store_membership

SHARING_LEVELS: tuple[str, ...] = ("S1", "S2", "S4")
FUSIONS: tuple[str, ...] = ("stacker", "noisy_or", "kofn")  # stacker is primary (A13)
PROPAGATION_WEIGHT = 0.5
AE_SAMPLE = 200_000
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2)


def _halves(windows: np.ndarray, v0: int, v1: int) -> np.ndarray:
    """Fold 0 = first half of the validation windows, fold 1 = second half."""
    return (windows >= v0 + (v1 - v0 + 1) // 2).astype(np.int8)


def stacker_scores(
    feats: pl.DataFrame,
    names: tuple[str, ...],
    label: np.ndarray,
    usable: np.ndarray,
    fold: np.ndarray,
    seed: int,
) -> np.ndarray:
    """Per member, two-fold by time: fit on one half, score the other."""
    out = feats["prob"].to_numpy().copy()
    x_all = feats.select(names).to_numpy().astype(np.float64)
    members = feats["member"].to_numpy()
    for m in np.unique(members):
        for k in (0, 1):
            fit = (members == m) & (fold == k) & usable
            apply = (members == m) & (fold != k)
            if not apply.any() or fit.sum() < 20 or len(np.unique(label[fit])) < 2:
                continue
            scaler = StandardScaler().fit(x_all[fit])
            model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=seed).fit(
                scaler.transform(x_all[fit]), label[fit]
            )
            out[apply] = model.predict_proba(scaler.transform(x_all[apply]))[:, 1]
    return out


def _flag_precision(
    alerted: np.ndarray,
    label: np.ndarray,
    usable: np.ndarray,
    members: np.ndarray,
    fold: np.ndarray,
) -> dict[tuple[int, int], float]:
    """Each member's own alert precision on each fold (the q of noisy-OR at S1)."""
    out = {}
    for m in np.unique(members):
        for k in (0, 1):
            sel = (members == m) & (fold == k) & usable & alerted
            out[(int(m), k)] = float(label[sel].mean()) if sel.any() else 0.0
    return out


def run_seed(
    paths: DatasetPaths,
    option: str,
    seed: int,
    reps: int,
    window_reps: int,
    meter: AnonPeak | None = None,
) -> dict[str, Any]:
    """Every configuration for one seed: scores and per-scheme outcomes."""
    t_start = time.perf_counter()
    memory: dict[str, float | None] = {}

    def lap(phase: str) -> None:
        if meter is not None:
            memory[phase] = meter.lap()

    plan = load_plan(paths)
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    pooled_f = FeatureStore(paths, option, "pooled")
    windows = training_windows(store, feats)
    cols = feature_sets()["all"]
    members = sorted(store.accounts_per_member()["member"].to_list())
    apm = store.accounts_per_member()
    lookback = int(feats.meta["neighbourhood"]["lookback_windows"])
    v0, v1 = (int(x) for x in store.meta["partition_windows"]["val"])
    seconds: dict[str, float] = {}

    # S0 detector, out-of-sample calibration, primary-budget alerts.
    t0 = time.perf_counter()
    models = fit_local_models(store, feats, cols, windows, seed, members)
    fn = _per_member(models)
    val = score_rows(store, feats, "val", fn)
    calibrators = _calibrators(score_rows(store, feats, "train", fn, windows.stop_from))
    prob = np.zeros(val.height)
    member_arr = val["member"].to_numpy()
    for m, cal in calibrators.items():
        idx = member_arr == m
        prob[idx] = cal(val["score"].to_numpy()[idx])
    keys = val.select(*KEY_COLUMNS)
    label = val["label"].to_numpy().astype(np.int8)
    usable = ~val["masked"].to_numpy()
    alerted = _alerts(keys, prob, apm, plan.window_hours)
    seconds["s0"] = round(time.perf_counter() - t0, 1)
    lap("s0")

    # Oracle: pooled rows and graph.
    t0 = time.perf_counter()
    fit, stop = training_rows(store, pooled_f, cols, windows, seed)
    oracle = GBDT(cols, seed).fit(fit.x, fit.y, fit.w, stop.x, stop.y, stop.w)
    del fit, stop
    oracle_score = score_rows(store, pooled_f, "val", oracle.score)["score"].to_numpy()
    seconds["oracle"] = round(time.perf_counter() - t0, 1)
    lap("oracle")

    # Records and candidates (with S4 embeddings).
    t0 = time.perf_counter()
    schema = load_evidence_schema()
    sample = sample_rows(feats, cols, windows, AE_SAMPLE, seed)
    encoders = {
        m: Autoencoder(cols, seed).fit(sample.filter(pl.col("member") == m))
        for m in members
        if sample.filter(pl.col("member") == m).height > 100
    }
    del sample
    keep = (prob >= schema.floor) | alerted
    counter_cols = [c[1] for c in schema.counters]
    chosen_parts, offset = [], 0
    for _, feat in slices(store, feats, "val"):
        n = feat.height
        sel = keep[offset : offset + n]
        chosen_parts.append(
            feat.filter(pl.Series(sel)).with_columns(pl.Series("row", np.nonzero(sel)[0] + offset))
        )
        offset += n
    chosen = pl.concat(chosen_parts)
    records: dict[int, pl.DataFrame] = {}
    cand_rows: list[np.ndarray] = []
    for m in members:
        part = chosen.filter(pl.col("member") == m)
        if part.height == 0 or m not in encoders:
            continue
        idx, direction, err = encoders[m].top(part, schema.top)
        r = part["row"].to_numpy()
        records[m] = build_records(
            part.select("member", "account", "window", *counter_cols),
            prob[r],
            alerted[r],
            idx,
            direction,
            err,
            encoders[m].embedding(part),
        )
        cand_rows.append(r)
    rows = np.sort(np.concatenate(cand_rows)) if cand_rows else np.zeros(0, dtype=np.int64)
    del chosen
    candidates = keys[rows].with_columns(
        pl.Series("prob", prob[rows]),
        pl.Series("prob_bucket", bucket(prob[rows], schema.prob_edges)),
    )
    edges = link_edges(
        paths.transactions,
        plan,
        v0,
        v1,
        lookback,
        store_membership(paths, option),
        touching=candidates.select("account"),
    )
    seconds["records"] = round(time.perf_counter() - t0, 1)
    lap("records")

    # Scores per configuration. Fusion and propagation change candidate rows only, so
    # they are kept for those rows and expanded one at a time (memory at scale).
    full_scores: dict[str, np.ndarray] = {"S0": prob, "oracle": oracle_score}
    row_scores: dict[str, np.ndarray] = {}
    protocol: dict[str, Any] = {}
    fold = _halves(candidates["window"].to_numpy(), v0, v1)
    flag_q = _flag_precision(
        alerted[rows], label[rows], usable[rows], candidates["member"].to_numpy(), fold
    )
    for level in SHARING_LEVELS:
        t0 = time.perf_counter()
        run = simulate(
            level, candidates.select(*KEY_COLUMNS, "prob_bucket"), records, edges, v0, lookback
        )
        assert run.responses is not None and run.inbound is not None and run.asked is not None
        ev = evidence_features(level, candidates, run.responses, run.inbound, run.asked)
        q = np.array(
            [flag_q[(int(m), int(1 - k))] for m, k in zip(ev["member"], fold, strict=True)]
        )  # precision on the *other* fold, as the stacker
        variants = {
            "stacker": stacker_scores(
                ev, feature_names(level), label[rows], usable[rows], fold, seed
            ),
            "noisy_or": _noisy_or_per_row(ev, level, q),
            "kofn": k_of_n(ev),
        }
        for fusion, s in variants.items():
            row_scores[f"{level}/{fusion}"] = np.asarray(s, dtype=np.float64)
        protocol[level] = {k: v for k, v in run.stats.items() if k not in ("messages",)} | {
            "messages": sum(run.stats.get("messages", {}).values()),
            "seconds_total": round(time.perf_counter() - t0, 1),
        }
        lap(level)
        del run, ev

    # Plaintext score propagation (no cryptography): own + w * max counterparty prob.
    t0 = time.perf_counter()
    row_scores["propagation"] = _propagation(prob, keys, candidates, rows, edges, lookback)[rows]
    names = [*full_scores, *row_scores]

    def score_of(name: str) -> np.ndarray:
        if name in full_scores:
            return full_scores[name]
        out = prob.copy()
        out[rows] = row_scores[name]
        return out

    seconds["propagation"] = round(time.perf_counter() - t0, 1)
    lap("propagation")

    # Evaluate every configuration.
    t0 = time.perf_counter()
    val_part = store.partition("val")
    # Linking edges must cover every configuration's final alerts (the oracle's can
    # fall outside S0's candidates), so they are cut to the union of all alerts.
    alert_accounts = pl.concat(
        [keys.filter(pl.Series(_alerts(keys, score_of(n), apm, plan.window_hours))) for n in names]
    ).select(pl.col("account").unique())
    full_edges = link_edges(paths.transactions, plan, v0, v1, lookback, touching=alert_accounts)
    linkers = {
        "local": Linker(full_edges, lookback, False),
        "pooled": Linker(full_edges, lookback, True),
    }
    results: dict[str, Any] = {}
    outcomes: dict[str, pl.DataFrame] = {}
    auprc: dict[str, float] = {}
    for name in names:
        s = score_of(name)
        auprc[name] = RankedScores(label[usable], s[usable]).stats()[0]
        out: dict[str, pl.DataFrame] = {}
        rep = evaluate(
            val_part,
            ScoreFrame(keys.with_columns(pl.Series("score", s))),
            accounts_per_member=apm,
            window_hours=plan.window_hours,
            thresholds={},
            budgets=(PRIMARY,),
            delay_windows=DELAY_WINDOWS,
            reps=reps,
            window_reps=window_reps,
            seed=seed,
            linker=linkers["local" if name == "S0" else "pooled"],
            linked_draws=0,
            outcomes=out,
        )
        results[name] = rep
        outcomes[name] = out[PRIMARY.name]
    seconds["evaluate"] = round(time.perf_counter() - t0, 1)
    lap("evaluate")
    seconds["total"] = round(time.perf_counter() - t_start, 1)
    return {
        "seed": seed,
        "results": results,
        "outcomes": outcomes,
        "protocol": protocol,
        "candidates": len(rows),
        "alerts": int(alerted.sum()),
        "seconds": seconds,
        "memory_mb": memory,
        "auprc": auprc,
    }


def _noisy_or_per_row(ev: pl.DataFrame, level: str, q: np.ndarray) -> np.ndarray:
    """Noisy-OR with a per-row flag precision (the member's, from the other fold)."""
    return noisy_or(ev, level, q)


def _alerts(keys: pl.DataFrame, score: np.ndarray, apm: pl.DataFrame, hours: int) -> np.ndarray:
    return (
        apply_budget(
            keys.with_columns(pl.Series("score", score)),
            PRIMARY,
            accounts_per_member=apm,
            window_hours=hours,
        )
        .join(keys.with_row_index("row"), on=list(KEY_COLUMNS))
        .sort("row")["alert"]
        .to_numpy()
    )


def _propagation(
    prob: np.ndarray,
    keys: pl.DataFrame,
    candidates: pl.DataFrame,
    rows: np.ndarray,
    edges: pl.DataFrame,
    lookback: int,
) -> np.ndarray:
    """Plaintext: each candidate adds w x its strongest cross-member counterparty's probability."""
    groups = counterparty_requests(
        candidates.select(*KEY_COLUMNS, "prob_bucket"), edges, lookback
    ).explode("account", empty_as_null=False)
    probs = keys.select(
        pl.col("account").alias("cp"), pl.col("window").alias("cp_window")
    ).with_columns(pl.Series("cp_prob", prob))
    best = (
        groups.join(probs, on="cp")
        .filter(
            (pl.col("cp_window") <= pl.col("window"))
            & (pl.col("cp_window") > pl.col("window") - lookback)
        )
        .group_by("member", "account", "window")
        .agg(pl.col("cp_prob").max().alias("cp_max"))
    )
    cand = (
        candidates.select(*KEY_COLUMNS)
        .with_columns(pl.Series("row", rows))
        .join(best, on=list(KEY_COLUMNS), how="left")
    )
    out = prob.copy()
    r = cand["row"].to_numpy()
    out[r] = prob[r] + PROPAGATION_WEIGHT * cand["cp_max"].fill_null(0.0).to_numpy()
    return out


def combine(seeds: list[dict[str, Any]], reps: int) -> dict[str, Any]:
    """Seed-averaged per-scheme outcomes, intervals and paired gains over S0."""
    names = list(seeds[0]["outcomes"])
    order = seeds[0]["outcomes"]["S0"]["scheme_id"]
    stack: dict[str, dict[str, np.ndarray]] = {}
    for name in names:
        per = {}
        for metric in ("linked", "detected", "linked_cross_member"):
            cols = []
            for s in seeds:
                o = s["outcomes"][name]
                assert o["scheme_id"].equals(order)
                cols.append(o[metric].to_numpy().astype(float))
            per[metric] = np.column_stack(cols)
        stack[name] = per
    summary: dict[str, Any] = {}
    for name in names:
        summary[name] = {
            m: scheme_rate_ci(stack[name][m], reps).to_dict()
            for m in ("linked", "detected", "linked_cross_member")
        }
        summary[name]["auprc_mean"] = float(np.mean([s["auprc"][name] for s in seeds]))
        if name != "S0":
            diff, p = paired_difference(
                stack[name]["linked"].mean(axis=1), stack["S0"]["linked"].mean(axis=1), reps
            )
            summary[name]["linked_gain"] = {"difference": diff.to_dict(), "p": p}
    summary["H1b"] = {
        level: _recovery(stack, level, reps) for level in ("S1/stacker", "S2/stacker", "S4/stacker")
    }
    return summary


def _recovery(stack: dict[str, dict[str, np.ndarray]], level: str, reps: int) -> dict[str, Any]:
    """(level - S0) / (oracle - S0) in linked detection, scheme bootstrap."""
    s0 = stack["S0"]["linked"].mean(axis=1)
    lv = stack[level]["linked"].mean(axis=1)
    orc = stack["oracle"]["linked"].mean(axis=1)
    point = (lv.mean() - s0.mean()) / max(orc.mean() - s0.mean(), 1e-12)
    rng = np.random.default_rng(0)
    n = len(s0)
    draws = []
    for _ in range(reps):
        i = rng.integers(0, n, n)
        den = orc[i].mean() - s0[i].mean()
        if den > 0:
            draws.append((lv[i].mean() - s0[i].mean()) / den)
    if orc.mean() - s0.mean() <= 0 or not draws:
        # No oracle gain to recover (e.g. the fixture, where the budget yields no alerts).
        return {"estimate": None, "low": None, "high": None, "reps": 0}
    return interval_from(np.asarray(draws), float(point)).to_dict()


def run_x1(
    paths: DatasetPaths,
    option: str = "B8",
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    reps: int = 1000,
    window_reps: int = 200,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        per_seed = []
        for seed in seeds:
            r = run_seed(paths, option, seed, reps, window_reps, anon)
            per_seed.append(r)
            if progress:
                progress(f"seed {seed}: {r['seconds']['total']:.0f} s")
        summary = combine(per_seed, reps)
        anon.lap()
        random_ref = _random_reference(paths, option, reps, window_reps)
        reference_mb = anon.lap()
    return {
        "dataset": paths.name,
        "option": option,
        "seeds": list(seeds),
        "primary_budget": PRIMARY.name,
        "delay_windows": DELAY_WINDOWS,
        "primary_fusion": "stacker",
        "summary": summary,
        "random": random_ref,
        "per_seed": [
            {
                "seed": r["seed"],
                "seconds": r["seconds"],
                "memory_mb": r["memory_mb"],
                "protocol": r["protocol"],
                "candidates": r["candidates"],
                "alerts": r["alerts"],
                "auprc": r["auprc"],
                "linked": {n: float(o["linked"].mean()) for n, o in r["outcomes"].items()},
            }
            for r in per_seed
        ],
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
        "reference_mb": reference_mb,
    }


def _random_reference(
    paths: DatasetPaths, option: str, reps: int, window_reps: int
) -> dict[str, Any]:
    """Random alerts at the same budget, linked with the pooled rule over every edge."""
    plan = load_plan(paths)
    store = EvalStore(paths, option)
    part: PartitionData = store.partition("val")
    lookback = int(FeatureStore(paths, option, "member").meta["neighbourhood"]["lookback_windows"])
    v0, v1 = (int(x) for x in store.meta["partition_windows"]["val"])
    edges = link_edges(paths.transactions, plan, v0, v1, lookback)
    rep = evaluate(
        part,
        random_scorer(part.labels.keys(), 0),
        accounts_per_member=store.accounts_per_member(),
        window_hours=plan.window_hours,
        thresholds={},
        budgets=(PRIMARY,),
        delay_windows=DELAY_WINDOWS,
        reps=reps,
        window_reps=window_reps,
        seed=0,
        linker=Linker(edges, lookback, True),
        linked_draws=20,
    )
    b = rep["budgets"][0]
    return {
        "detected": b["random_alert_detected"],
        "linked": b["random_alert_linked"],
    }
