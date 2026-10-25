"""Week 5: the local-only (S0) and pooled-oracle reference points (Gate G1).

Configurations, all trained on the training partition and evaluated on
validation through the harness:

* ``S0-B``: local LightGBM per member on behaviour and history features;
* ``S0-BG``: local LightGBM per member on every feature (behaviour + graph);
  this is S0, the no-sharing baseline every sharing level is compared with;
* ``oracle``: one LightGBM on all members' rows with pooled-view features
  (every transaction visible) and pooled linking: the upper bound;
* ``iforest`` and ``pca``: unsupervised per-member floor, every feature;
* ``random`` and ``activity``: the harness reference scorers.

S0 configurations link alerts locally (finmesh.fusion.local); the oracle
links across members. Linked and any-alert scheme detection are reported
against the random-alert baseline at the same budget. FPR thresholds come
from the held-out end of the training period (out of sample for every
model); thresholds and calibration for the test run come from validation.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression

from finmesh.eval.budgets import DEFAULT_BUDGETS, Budget, fit_thresholds
from finmesh.eval.guard import KEY_COLUMNS, ScoreFrame
from finmesh.eval.harness import evaluate, random_scorer
from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.eval.stats import holm, interval_from, paired_difference
from finmesh.features.build import FeatureStore
from finmesh.features.schema import load_schema
from finmesh.fusion.local import Linker, link_edges
from finmesh.models.calibration import Isotonic
from finmesh.models.gbdt import GBDT
from finmesh.models.unsupervised import Unsupervised
from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak
from finmesh.training.data import Windows, sample_rows, slices, training_rows, training_windows

PRIMARY = Budget("per_1000_per_day", 1.0)  # amendment A10
DELAY_WINDOWS = 12  # 72 h after a scheme's first window (preregistered)
UNSUPERVISED_SAMPLE = 200_000
HEADLINE = ("S0-BG", "oracle")

FeatureFn = Callable[[pl.DataFrame], np.ndarray]


def feature_sets() -> dict[str, tuple[str, ...]]:
    s = load_schema()
    return {
        "behaviour": (*s.family("behaviour"), *s.family("history")),
        "all": s.names,
    }


def _per_member(models: dict[int, Any]) -> FeatureFn:
    def score(feat: pl.DataFrame) -> np.ndarray:
        out = np.zeros(feat.height)
        members = feat["member"].to_numpy()
        for m, model in models.items():
            idx = members == m
            if idx.any():
                out[idx] = model.score(feat.filter(pl.Series(idx)))
        return out

    return score


def score_rows(
    store: EvalStore,
    features: FeatureStore,
    partition: str,
    fn: FeatureFn,
    window_from: int | None = None,
) -> pl.DataFrame:
    """Keys, score, label, masked for a partition (optionally from a window on)."""
    parts = []
    for lab, feat in slices(store, features, partition):
        if window_from is not None:
            keep = lab["window"] >= window_from
            lab, feat = lab.filter(keep), feat.filter(keep)
        parts.append(
            lab.select(*KEY_COLUMNS, "label", "masked").with_columns(
                pl.Series("score", fn(feat), dtype=pl.Float64)
            )
        )
    return pl.concat(parts)


class ScoreBook:
    """One key-and-label frame per partition, one score array per scorer.

    Keeping a full frame per scorer cost about 1.5 GB at HI-Medium scale.
    """

    def __init__(self) -> None:
        self.base: dict[str, pl.DataFrame] = {}
        self.arrays: dict[tuple[str, str], np.ndarray] = {}

    def add(self, name: str, part: str, frame: pl.DataFrame) -> None:
        if part not in self.base:
            self.base[part] = frame.drop("score")
        self.arrays[(name, part)] = frame["score"].to_numpy()

    def frame(self, name: str, part: str) -> pl.DataFrame:
        return self.base[part].with_columns(pl.Series("score", self.arrays[(name, part)]))

    def names(self) -> list[str]:
        return [n for n, p in self.arrays if p == "val"]


def _fpr_thresholds(scored: pl.DataFrame) -> dict[str, pl.DataFrame]:
    return {b.name: fit_thresholds(scored, b) for b in DEFAULT_BUDGETS if b.kind == "fpr"}


def _isotonic(scores: np.ndarray, y: np.ndarray) -> Isotonic:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(scores, y)
    return Isotonic(tuple(map(float, iso.X_thresholds_)), tuple(map(float, iso.y_thresholds_)))


def _ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    order = np.argsort(p)
    chunks = np.array_split(order, bins)
    return float(sum(abs(p[c].mean() - y[c].mean()) * len(c) for c in chunks if len(c)) / len(p))


def calibration(scored: pl.DataFrame) -> dict[str, Any]:
    """Per-member isotonic fit on validation; quality from two-fold cross-fitting."""
    ev = scored.filter(~pl.col("masked"))
    fold = (pl.col("account").hash(seed=17) % 2).alias("fold")
    ev = ev.with_columns(fold)
    calibrated = np.zeros(ev.height)
    fitted: dict[str, Any] = {}
    for m in sorted(ev["member"].unique().to_list()):
        for k in (0, 1):
            tr = ev.filter((pl.col("member") == m) & (pl.col("fold") == k))
            te_mask = ((ev["member"] == m) & (ev["fold"] != k)).to_numpy()
            if tr.height and tr["label"].sum() > 0 and te_mask.any():
                f = _isotonic(tr["score"].to_numpy(), tr["label"].to_numpy())
                calibrated[te_mask] = f(ev["score"].to_numpy()[te_mask])
        whole = ev.filter(pl.col("member") == m)
        if whole["label"].sum() > 0:
            fitted[str(m)] = _isotonic(
                whole["score"].to_numpy(), whole["label"].to_numpy()
            ).to_dict()
    y = ev["label"].to_numpy().astype(np.float64)
    raw = np.clip(ev["score"].to_numpy(), 0.0, 1.0)
    return {
        "brier_raw": float(np.mean((raw - y) ** 2)),
        "brier_calibrated_crossfit": float(np.mean((calibrated - y) ** 2)),
        "ece_raw": _ece(raw, y),
        "ece_calibrated_crossfit": _ece(calibrated, y),
        "prevalence": float(y.mean()),
        "calibrators": fitted,
    }


def _paired_window(a: pl.DataFrame, b: pl.DataFrame, reps: int, seed: int) -> dict[str, Any]:
    """AUPRC(a) - AUPRC(b) on the same rows, same Poisson weights per account."""
    ev_a, ev_b = a.filter(~pl.col("masked")), b.filter(~pl.col("masked"))
    y = ev_a["label"].to_numpy()
    clusters = ev_a["account"].to_numpy()
    ra, rb = RankedScores(y, ev_a["score"].to_numpy()), RankedScores(y, ev_b["score"].to_numpy())
    (ap_a, _), (ap_b, _) = ra.stats(), rb.stats()
    reps_a, _ = ra.bootstrap(clusters, reps, seed)
    reps_b, _ = rb.bootstrap(clusters, reps, seed)
    diff = reps_a - reps_b
    p = float(min(1.0, 2 * min((diff <= 0).mean(), (diff >= 0).mean())))
    return {"auprc_difference": interval_from(diff, ap_a - ap_b).to_dict(), "p": p}


def run_baselines(
    paths: DatasetPaths,
    option: str = "B8",
    seed: int = 0,
    reps: int = 1000,
    window_reps: int = 200,
    linked_draws: int = 20,
) -> dict[str, Any]:
    plan = load_plan(paths)
    store = EvalStore(paths, option)
    member_f = FeatureStore(paths, option, "member")
    pooled_f = FeatureStore(paths, option, "pooled")
    windows: Windows = training_windows(store, member_f)
    sets = feature_sets()
    members = sorted(store.accounts_per_member()["member"].to_list())
    lookback = int(member_f.meta["neighbourhood"]["lookback_windows"])
    v0, v1 = store.meta["partition_windows"]["val"]
    edges = link_edges(paths.transactions, plan, int(v0), int(v1), lookback)
    linkers = {"local": Linker(edges, lookback, False), "pooled": Linker(edges, lookback, True)}

    book = ScoreBook()
    info: dict[str, dict[str, Any]] = {}

    def record(name: str, t0: float, extra: dict[str, Any]) -> None:
        info[name] = {**extra, "seconds": round(time.perf_counter() - t0, 1)}

    # Reference scorers (label-free) on validation; thresholds from the held-out window span.
    def random_fn(feat: pl.DataFrame) -> np.ndarray:
        return random_scorer(feat.select(*KEY_COLUMNS), seed).frame["score"].to_numpy()

    def activity_fn(feat: pl.DataFrame) -> np.ndarray:
        return (feat["tx_out"] + feat["tx_in"] + 2 * feat["self_tx"]).to_numpy()

    reference: dict[str, FeatureFn] = {"random": random_fn, "activity": activity_fn}
    for name, ref in reference.items():
        t0 = time.perf_counter()
        book.add(name, "val", score_rows(store, member_f, "val", ref))
        book.add(name, "stop", score_rows(store, member_f, "train", ref, windows.stop_from))
        record(name, t0, {"view": "member", "linker": "local"})

    # Local LightGBM per member: behaviour only, then every feature.
    importance: dict[str, dict[str, float]] = {}
    for name, cols in (("S0-B", sets["behaviour"]), ("S0-BG", sets["all"])):
        t0 = time.perf_counter()
        fit, stop = training_rows(store, member_f, cols, windows, seed)
        models: dict[int, GBDT] = {}
        for m in members:
            fi, si = fit.member == m, stop.member == m
            if fit.y[fi].sum() == 0 or stop.y[si].sum() == 0:
                continue
            models[m] = GBDT(cols, seed).fit(
                fit.x[fi], fit.y[fi], fit.w[fi], stop.x[si], stop.y[si], stop.w[si]
            )
        del fit, stop
        local_fn = _per_member(models)
        book.add(name, "val", score_rows(store, member_f, "val", local_fn))
        book.add(name, "stop", score_rows(store, member_f, "train", local_fn, windows.stop_from))
        imp = [mdl.importance() for mdl in models.values()]
        importance[name] = {c: float(np.mean([i[c] for i in imp])) for c in cols} if imp else {}
        record(
            name,
            t0,
            {
                "view": "member",
                "linker": "local",
                "features": len(cols),
                "members_trained": len(models),
                "models": {str(m): mdl.info for m, mdl in models.items()},
            },
        )

    # Pooled oracle: every member's rows, the full graph.
    t0 = time.perf_counter()
    fit, stop = training_rows(store, pooled_f, sets["all"], windows, seed)
    oracle = GBDT(sets["all"], seed).fit(fit.x, fit.y, fit.w, stop.x, stop.y, stop.w)
    del fit, stop
    book.add("oracle", "val", score_rows(store, pooled_f, "val", oracle.score))
    book.add(
        "oracle", "stop", score_rows(store, pooled_f, "train", oracle.score, windows.stop_from)
    )
    importance["oracle"] = oracle.importance()
    record("oracle", t0, {"view": "pooled", "linker": "pooled", "model": oracle.info})

    # Unsupervised floor per member.
    for kind in ("iforest", "pca"):
        t0 = time.perf_counter()
        sample = sample_rows(member_f, sets["all"], windows, UNSUPERVISED_SAMPLE, seed)
        umodels = {
            m: Unsupervised(kind, sets["all"], seed).fit(sample.filter(pl.col("member") == m))
            for m in members
            if sample.filter(pl.col("member") == m).height > 10
        }
        del sample
        unsup_fn = _per_member(umodels)
        book.add(kind, "val", score_rows(store, member_f, "val", unsup_fn))
        book.add(kind, "stop", score_rows(store, member_f, "train", unsup_fn, windows.stop_from))
        record(
            kind,
            t0,
            {
                "view": "member",
                "linker": "local",
                "models": {str(m): u.info for m, u in umodels.items()},
            },
        )

    # Evaluation through the harness.
    val = store.partition("val")
    val_touch = store.partition("val", variant="touch")
    apm = store.accounts_per_member()
    budgets = (PRIMARY, *[b for b in DEFAULT_BUDGETS if b.kind == "fpr"])
    results: dict[str, Any] = {}
    outcomes: dict[str, dict[str, pl.DataFrame]] = {}
    for name in book.names():
        t0 = time.perf_counter()
        outcomes[name] = {}
        results[name] = evaluate(
            val,
            ScoreFrame(book.frame(name, "val").select(*KEY_COLUMNS, "score")),
            accounts_per_member=apm,
            window_hours=plan.window_hours,
            thresholds=_fpr_thresholds(book.frame(name, "stop")),
            budgets=budgets,
            delay_windows=DELAY_WINDOWS,
            reps=reps,
            window_reps=window_reps,
            seed=seed,
            linker=linkers[info[name]["linker"]],
            linked_draws=linked_draws,
            outcomes=outcomes[name],
        )
        info[name]["evaluate_seconds"] = round(time.perf_counter() - t0, 1)

    sensitivity = {
        name: evaluate(
            val_touch,
            ScoreFrame(book.frame(name, "val").select(*KEY_COLUMNS, "score")),
            accounts_per_member=apm,
            window_hours=plan.window_hours,
            thresholds=_fpr_thresholds(book.frame(name, "stop")),
            budgets=(PRIMARY,),
            delay_windows=DELAY_WINDOWS,
            reps=reps,
            window_reps=window_reps,
            seed=seed,
            linker=linkers[info[name]["linker"]],
            linked_draws=linked_draws,
        )
        for name in HEADLINE
    }

    del val_touch
    comparisons = _comparisons(book, outcomes, reps, window_reps, seed)
    calib = {name: calibration(book.frame(name, "val")) for name in HEADLINE}
    test_thresholds = {
        name: {k: v.to_dicts() for k, v in _fpr_thresholds(book.frame(name, "val")).items()}
        for name in HEADLINE
    }
    return {
        "dataset": paths.name,
        "option": option,
        "seed": seed,
        "windows": windows.to_dict(),
        "validation_windows": [int(v0), int(v1)],
        "primary_budget": PRIMARY.name,
        "delay_windows": DELAY_WINDOWS,
        "label_rule": store.meta.get("label_rule"),
        "configurations": info,
        "results": results,
        "sensitivity_touch_label": sensitivity,
        "comparisons": comparisons,
        "calibration": calib,
        "importance": importance,
        "thresholds_for_test": test_thresholds,
    }


def _comparisons(
    book: ScoreBook,
    outcomes: dict[str, dict[str, pl.DataFrame]],
    reps: int,
    window_reps: int,
    seed: int,
) -> dict[str, Any]:
    """Paired differences for G1 (oracle vs S0) and PT4b (graph vs behaviour)."""
    pairs = (("oracle", "S0-BG"), ("S0-BG", "S0-B"), ("S0-BG", "random"))
    out: dict[str, Any] = {}
    pvalues: list[float] = []
    keys: list[tuple[str, str]] = []
    for a, b in pairs:
        oa, ob = outcomes[a][PRIMARY.name], outcomes[b][PRIMARY.name]
        entry: dict[str, Any] = {
            "window": _paired_window(book.frame(a, "val"), book.frame(b, "val"), window_reps, seed)
        }
        for metric in ("linked", "detected"):
            diff, p = paired_difference(
                oa[metric].to_numpy().astype(float), ob[metric].to_numpy().astype(float), reps, seed
            )
            entry[metric] = {"difference": diff.to_dict(), "p": p}
            pvalues.append(p)
            keys.append((f"{a} - {b}", metric))
        out[f"{a} - {b}"] = entry
    for (pair, metric), adj in zip(keys, holm(pvalues), strict=True):
        out[pair][metric]["p_holm"] = adj
    return out


def run_with_memory(paths: DatasetPaths, **kwargs: Any) -> dict[str, Any]:
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        result = run_baselines(paths, **kwargs)
    result["seconds"] = round(time.perf_counter() - t0, 1)
    result["peak_anon_mb"] = anon.mb
    return result
