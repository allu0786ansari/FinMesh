"""Week 6: an in-process run of the sharing protocol on validation (S0, S1, S2).

Every member runs its S0 detector (local LightGBM, every feature), calibrated
on the held-out end of the training period (out of sample), and alerts at
the primary budget. It builds evidence records with its local autoencoder's
top deviations. Then each sharing level runs the protocol of
``finmesh.sharing.simulate``, and the harness scores the incidents:

* S0 links only a member's own alerts (``finmesh.fusion.local``);
* S1 and S2 add the cross-member links the protocol found;
* the decomposition from G1 (S0 alerts with the pooled rule) is the upper
  bound for linking S0's alerts.

Week 6 links on alert flags only, so S1 and S2 link the same alerts by
design; S2's richer records start to matter when week 7's fusion and triage
use them to re-rank each member's queue within its budget.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import polars as pl

from finmesh.eval.budgets import apply_budget
from finmesh.eval.guard import KEY_COLUMNS, ScoreFrame
from finmesh.eval.harness import evaluate
from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.eval.stats import paired_difference
from finmesh.features.build import FeatureStore
from finmesh.fusion.local import Linker, incidents, link_edges
from finmesh.models.autoencoder import Autoencoder
from finmesh.models.calibration import Isotonic
from finmesh.paths import DatasetPaths
from finmesh.sharing.evidence import bucket, build_records, load_evidence_schema
from finmesh.sharing.simulate import simulate
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import (
    DELAY_WINDOWS,
    PRIMARY,
    _isotonic,
    _per_member,
    feature_sets,
    fit_local_models,
    score_rows,
)
from finmesh.training.data import sample_rows, slices, training_windows

LEVELS: tuple[str, ...] = ("S0", "S1", "S2")
AE_SAMPLE = 200_000


def _calibrators(stop: pl.DataFrame) -> dict[int, Isotonic]:
    out = {}
    ev = stop.filter(~pl.col("masked"))
    for m in sorted(ev["member"].unique().to_list()):
        part = ev.filter(pl.col("member") == m)
        if part["label"].sum() > 0:
            out[int(m)] = _isotonic(part["score"].to_numpy(), part["label"].to_numpy())
    return out


def run_sharing(
    paths: DatasetPaths,
    option: str = "B8",
    seed: int = 0,
    reps: int = 1000,
    window_reps: int = 200,
    levels: tuple[str, ...] = LEVELS,
) -> dict[str, Any]:
    plan = load_plan(paths)
    store = EvalStore(paths, option)
    feats = FeatureStore(paths, option, "member")
    windows = training_windows(store, feats)
    cols = feature_sets()["all"]
    members = sorted(store.accounts_per_member()["member"].to_list())
    apm = store.accounts_per_member()
    lookback = int(feats.meta["neighbourhood"]["lookback_windows"])
    v0, v1 = (int(x) for x in store.meta["partition_windows"]["val"])
    timings: dict[str, float] = {}
    memory: dict[str, float | None] = {}
    meter = AnonPeak().__enter__()

    # 1. S0 detector, calibration out of sample, alerts at the primary budget.
    t0 = time.perf_counter()
    models = fit_local_models(store, feats, cols, windows, seed, members)
    fn = _per_member(models)
    val = score_rows(store, feats, "val", fn)
    stop = score_rows(store, feats, "train", fn, windows.stop_from)
    calibrators = _calibrators(stop)
    prob = np.zeros(val.height)
    member_arr = val["member"].to_numpy()
    for m, cal in calibrators.items():
        idx = member_arr == m
        prob[idx] = cal(val["score"].to_numpy()[idx])
    alerted = (
        apply_budget(
            val.select(*KEY_COLUMNS, "score"),
            PRIMARY,
            accounts_per_member=apm,
            window_hours=plan.window_hours,
        )
        .sort(*KEY_COLUMNS)
        .join(val.select(*KEY_COLUMNS).with_row_index("row"), on=KEY_COLUMNS)
        .sort("row")["alert"]
        .to_numpy()
    )
    del stop, models
    timings["detector"] = round(time.perf_counter() - t0, 1)
    memory["detector"] = meter.lap()

    # 2. Local autoencoders and evidence records (rows at the floor or alerted).
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
    rows = []
    offset = 0
    for _, feat in slices(store, feats, "val"):
        n = feat.height
        sel = keep[offset : offset + n]
        rows.append(
            feat.filter(pl.Series(sel)).with_columns(pl.Series("row", np.nonzero(sel)[0] + offset))
        )
        offset += n
    chosen = pl.concat(rows)
    rec_parts = {}
    for m in members:
        part = chosen.filter(pl.col("member") == m)
        if part.height == 0 or m not in encoders:
            continue
        idx, direction, err = encoders[m].top(part, schema.top)
        r = part["row"].to_numpy()
        rec_parts[m] = build_records(
            part.select("member", "account", "window", *counter_cols),
            prob[r],
            alerted[r],
            idx,
            direction,
            err,
        )
    timings["records"] = round(time.perf_counter() - t0, 1)
    memory["records"] = meter.lap()

    # 3. Alerts as the protocol sees them, and the transactions between members.
    alerts = (
        val.select(*KEY_COLUMNS)
        .with_columns(pl.Series("prob_bucket", bucket(prob, schema.prob_edges)))
        .filter(pl.Series(alerted))
    )
    edges = link_edges(
        paths.transactions,
        plan,
        v0,
        v1,
        lookback,
        store_membership(paths, option),
        touching=alerts.select("account"),
    )
    memory["edges"] = meter.lap()

    # 4. Each level: protocol, incidents, evaluation.
    val_part = store.partition("val")
    scores = ScoreFrame(val.select(*KEY_COLUMNS, "score"))
    alert_keys = alerts.select(KEY_COLUMNS)
    results: dict[str, Any] = {}
    protocol: dict[str, Any] = {}
    outcomes: dict[str, dict[str, pl.DataFrame]] = {}
    for level in levels:
        t0 = time.perf_counter()
        run = simulate(level, alerts, rec_parts, edges, v0, lookback)
        inc = incidents(alert_keys, edges, lookback, cross_member=False, extra=run.links)
        per_incident = inc.group_by("incident").agg(pl.col("member").n_unique().alias("members"))
        run.stats["cross_member_incidents"] = int((per_incident["members"] >= 2).sum())
        outcomes[level] = {}
        results[level] = evaluate(
            val_part,
            scores,
            accounts_per_member=apm,
            window_hours=plan.window_hours,
            thresholds={},
            budgets=(PRIMARY,),
            delay_windows=DELAY_WINDOWS,
            incidents=inc,
            reps=reps,
            window_reps=window_reps,
            seed=seed,
            outcomes=outcomes[level],
        )
        protocol[level] = {**run.stats, "total_seconds": round(time.perf_counter() - t0, 1)}
        memory[level] = meter.lap()
        del run, inc

    # Reference: S0's alerts linked with the pooled rule (the linking upper bound).
    results["S0+pooled-link"] = evaluate(
        val_part,
        scores,
        accounts_per_member=apm,
        window_hours=plan.window_hours,
        thresholds={},
        budgets=(PRIMARY,),
        delay_windows=DELAY_WINDOWS,
        reps=reps,
        window_reps=window_reps,
        seed=seed,
        linker=Linker(edges.select("src", "dst", "window"), lookback, True),
        linked_draws=0,
        outcomes=outcomes.setdefault("S0+pooled-link", {}),
    )
    comparisons = {}
    for level in [lv for lv in levels if lv != "S0"] + ["S0+pooled-link"]:
        a = outcomes[level][PRIMARY.name]["linked"].to_numpy().astype(float)
        b = outcomes["S0"][PRIMARY.name]["linked"].to_numpy().astype(float)
        diff, p = paired_difference(a, b, reps, seed)
        comparisons[f"{level} - S0"] = {"linked": diff.to_dict(), "p": p}
    phases = {**memory, "reference": meter.lap()}
    meter.__exit__(None, None, None)
    return {
        "dataset": paths.name,
        "option": option,
        "seed": seed,
        "windows": windows.to_dict(),
        "validation_windows": [v0, v1],
        "lookback_windows": lookback,
        "primary_budget": PRIMARY.name,
        "delay_windows": DELAY_WINDOWS,
        "evidence_schema_sha256": schema.sha256,
        "alerts": int(alerted.sum()),
        "records": {str(m): r.height for m, r in rec_parts.items()},
        "autoencoders": {str(m): e.info for m, e in encoders.items()},
        "protocol": protocol,
        "results": results,
        "comparisons": comparisons,
        "timings": timings,
        "peak_mb_by_phase": phases,
    }


def store_membership(paths: DatasetPaths, option: str) -> pl.DataFrame:
    return pl.read_parquet(paths.parquet / f"membership_{option}.parquet")


def run_with_memory(paths: DatasetPaths, **kwargs: Any) -> dict[str, Any]:
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        result = run_sharing(paths, **kwargs)
    result["seconds"] = round(time.perf_counter() - t0, 1)
    result["peak_anon_mb"] = anon.mb
    return result
