"""Experiment X6 (week 13; amendment A20): pattern attribution by sharing level.

How much does what banks share help an analyst name the laundering pattern
of a case? For each frozen level (S0, S1, S2, S3 at ε = 2, and the pooled
oracle as ceiling), per seed:

1. the level's final validation scores (frozen G2 fusion) give primary-budget
   alerts, linked into incidents by the level's rule (local for S0, pooled
   otherwise), exactly as in X1;
2. each pattern-labelled validation scheme is attributed through the incident
   holding most of its alerted accounts within 72 h (undetected otherwise);
3. the incident becomes a feature vector holding only what the level reveals
   to the incident's owner (the member with most of its rows): own features;
   S1 adds cross-member structure; S2 adds other members' record counters; S3
   the same counters through k-RR at ε/20 per field; the oracle sees pooled
   features of every row;
4. a multinomial LightGBM attributor, cross-fitted on the two time halves of
   validation, against three baselines: majority class, a rule-based shape
   detector and catalogue signature matching
   (``finmesh/schemas/typology_catalogue.json``).

Primary metric: end-to-end pattern accuracy over all pattern-labelled schemes
(undetected = wrong), averaged over seeds, scheme bootstrap. **H3a** holds on
validation when S2 − S0 attributor accuracy has a 95% CI above 0 and S2's
attributor beats the majority and rule baselines.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier
from sklearn.metrics import f1_score

from finmesh.eval.guard import KEY_COLUMNS
from finmesh.eval.schemes import _within_delay
from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.features.build import FeatureStore
from finmesh.fusion.local import Linker, link_edges
from finmesh.models.gbdt import matrix
from finmesh.paths import DatasetPaths
from finmesh.sharing.evidence import bucket, load_evidence_schema
from finmesh.sharing.ldp import k_rr
from finmesh.sysinfo import AnonPeak
from finmesh.training.baselines import DELAY_WINDOWS, feature_sets
from finmesh.training.data import slices
from finmesh.training.x1 import _alerts, _halves, run_seed

CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "schemas" / "typology_catalogue.json"
S3_EPSILON = 2.0
LEVELS: dict[str, str] = {
    "S0": "S0",
    "S1": "S1/stacker",
    "S2": "S2/stacker",
    "S3": f"S3[eps={S3_EPSILON:g}]/stacker",
    "oracle": "oracle",
}
METHODS: tuple[str, ...] = ("attributor", "majority", "rules", "catalogue")
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2)
KEYS = list(KEY_COLUMNS)
ATTRIBUTOR: dict[str, Any] = {
    "n_estimators": 200,
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_child_samples": 5,
    "class_weight": "balanced",
    "verbose": -1,
}


def load_catalogue() -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(CATALOGUE_PATH.read_text())
    return doc


# --------------------------------------------------------------------------- incidents
def gather_rows(
    store: EvalStore, feats: FeatureStore, rows: np.ndarray, cols: tuple[str, ...]
) -> np.ndarray:
    """Feature matrix of the given validation rows (sorted, in the keys' row order)."""
    out = np.full((len(rows), len(cols)), np.nan)
    offset = 0
    for _, feat in slices(store, feats, "val"):
        n = feat.height
        lo, hi = np.searchsorted(rows, offset), np.searchsorted(rows, offset + n)
        if hi > lo:
            out[lo:hi] = matrix(feat[rows[lo:hi] - offset], cols)
        offset += n
    return out


def best_incident(scheme_windows: pl.DataFrame, incidents: pl.DataFrame) -> pl.DataFrame:
    """scheme_id -> the incident holding most of its alerted accounts (ties: rows, low id)."""
    hit = scheme_windows.join(incidents.select(*KEYS, "incident"), on=KEYS)
    per = hit.group_by("scheme_id", "incident").agg(
        pl.col("account").n_unique().alias("accounts"), pl.len().alias("rows")
    )
    return (
        per.sort(
            ["scheme_id", "accounts", "rows", "incident"], descending=[False, True, True, False]
        )
        .group_by("scheme_id", maintain_order=True)
        .first()
        .select("scheme_id", "incident")
    )


def _agg(frame: pl.DataFrame, names: list[str], prefix: str) -> pl.DataFrame:
    """Mean and max of each column per incident (nulls ignored)."""
    return frame.group_by("incident").agg(
        *[pl.col(c).mean().alias(f"{prefix}_mean_{c}") for c in names],
        *[pl.col(c).max().alias(f"{prefix}_max_{c}") for c in names],
    )


def _with_nan_as_null(x: np.ndarray, names: list[str]) -> pl.DataFrame:
    return pl.DataFrame(x, schema=names, orient="row").fill_nan(None)


def incident_features(
    level: str,
    inc: pl.DataFrame,
    x_member: np.ndarray,
    x_pooled: np.ndarray | None,
    cols: tuple[str, ...],
    seed: int,
) -> pl.DataFrame:
    """One row per incident with only what ``level`` reveals to the incident's owner.

    ``inc``: member, account, window, incident, pos (row of ``x_member`` / ``x_pooled``).
    """
    names = list(cols)
    counts = inc.group_by("incident").agg(
        pl.len().alias("n_rows"),
        pl.col("account").n_unique().alias("n_accounts"),
        pl.col("member").n_unique().alias("n_members"),
        (pl.col("window").max() - pl.col("window").min() + 1).alias("span"),
    )
    if level == "oracle":
        assert x_pooled is not None
        allx = _with_nan_as_null(x_pooled[inc["pos"].to_numpy()], names).with_columns(
            inc["incident"]
        )
        return counts.join(_agg(allx, names, "all"), on="incident")
    owner = (
        inc.group_by("incident", "member")
        .agg(pl.len().alias("n"))
        .sort(["incident", "n", "member"], descending=[False, True, False])
        .group_by("incident", maintain_order=True)
        .first()
        .select("incident", pl.col("member").alias("owner"))
    )
    inc = inc.join(owner, on="incident")
    own = inc.filter(pl.col("member") == pl.col("owner"))
    ownx = _with_nan_as_null(x_member[own["pos"].to_numpy()], names).with_columns(own["incident"])
    out = own.group_by("incident").agg(
        pl.len().alias("own_rows"),
        pl.col("account").n_unique().alias("own_accounts"),
        (pl.col("window").max() - pl.col("window").min() + 1).alias("own_span"),
    )
    out = out.join(_agg(ownx, names, "own"), on="incident")
    if level == "S0":
        return out
    out = out.join(counts, on="incident")
    if level == "S1":
        return out
    # S2 / S3: other members' evidence-record counters (bucketed; S3 through k-RR).
    schema = load_evidence_schema()
    other = inc.filter(pl.col("member") != pl.col("owner"))
    pos = other["pos"].to_numpy()
    rng = np.random.default_rng([seed, 31, 3])
    data: dict[str, np.ndarray] = {}
    for name, feature, edges in schema.counters:
        b = bucket(x_member[pos, names.index(feature)], edges).astype(np.int64)
        if level == "S3":
            b = k_rr(b, tuple(range(len(edges) + 2)), S3_EPSILON / 20.0, rng)
        data[f"c_{name}"] = b.astype(np.float64)
    rec = pl.DataFrame(data).with_columns(other["incident"])
    if rec.height:
        out = out.join(_agg(rec, list(data), "rec"), on="incident", how="left")
    else:
        out = out.with_columns(
            *[pl.lit(None, pl.Float64).alias(f"rec_{s}_{c}") for c in data for s in ("mean", "max")]
        )
    return out


# --------------------------------------------------------------------------- shape and baselines
def shape(frame: pl.DataFrame, level: str) -> np.ndarray:
    """The catalogue's shape signature, from what ``level`` can see (rows: incidents)."""
    p = "all" if level == "oracle" else "own"

    def col(name: str) -> np.ndarray:
        return frame[name].cast(pl.Float64).fill_null(np.nan).to_numpy()

    def mx(*names: str) -> np.ndarray:
        stacked = np.stack([col(f"{p}_max_{n}") for n in names])
        out = stacked[0]
        for row in stacked[1:]:
            out = np.fmax(out, row)  # NaN only where every input is NaN, without a warning
        return np.asarray(out)

    accounts = col("own_accounts") if level == "S0" else col("n_accounts")
    members = np.ones(frame.height) if level == "S0" else col("n_members")
    with np.errstate(all="ignore"):
        return np.stack(
            [
                col(f"{p}_max_fan_in"),
                col(f"{p}_max_fan_out"),
                col(f"{p}_max_gs_min_fan"),
                mx("cyc2", "cyc3", "cyc4"),
                mx("sg_out_max", "sg_in_max"),
                col(f"{p}_mean_pass_through"),
                accounts,
                members,
            ],
            axis=1,
        )


def rule_predict(sig: np.ndarray, catalogue: dict[str, Any]) -> np.ndarray:
    names = catalogue["shape_features"]
    out = np.full(len(sig), catalogue["rules"]["otherwise"], dtype=object)
    decided = np.zeros(len(sig), dtype=bool)
    for rule in catalogue["rules"]["order"]:
        hit = np.ones(len(sig), dtype=bool)
        for feat, (op, value) in rule["when"].items():
            v = sig[:, names.index(feat)]
            with np.errstate(invalid="ignore"):
                hit &= (v >= value) if op == ">=" else (v <= value)
        take = hit & ~decided
        out[take] = rule["pattern"]
        decided |= take
    return out


def catalogue_predict(
    sig: np.ndarray, train_sig: np.ndarray, catalogue: dict[str, Any]
) -> np.ndarray:
    names = catalogue["shape_features"]
    with np.errstate(all="ignore"):
        mu = np.nanmean(train_sig, axis=0) if len(train_sig) else np.zeros(len(names))
        sd = np.nanstd(train_sig, axis=0) if len(train_sig) else np.ones(len(names))
    mu = np.nan_to_num(mu)
    sd = np.where(np.nan_to_num(sd) > 0, np.nan_to_num(sd), 1.0)
    z = np.nan_to_num((sig - mu) / sd)
    entries = catalogue["entries"]
    proto = np.array([[e["signature"].get(n, 0) for n in names] for e in entries], dtype=float)
    proto /= np.linalg.norm(proto, axis=1, keepdims=True)
    zn = z / np.maximum(np.linalg.norm(z, axis=1, keepdims=True), 1e-12)
    return np.array([entries[i]["id"] for i in np.argmax(zn @ proto.T, axis=1)], dtype=object)


def attribute(
    table: pl.DataFrame,
    level: str,
    seed: int,
    catalogue: dict[str, Any],
    proba_out: dict[str, Any] | None = None,
) -> dict[str, np.ndarray]:
    """Cross-fitted predictions per method for every scheme row (None if undetected).

    ``proba_out`` (week 14, A21) receives the attributor's cross-fitted class
    probabilities: ``classes`` (catalogue order) and ``p`` (rows x classes; NaN
    rows for undetected schemes). Predictions are unchanged by asking for them.
    """
    detected = table["incident"].is_not_null().to_numpy()
    y = table["pattern"].to_numpy()
    fold = table["fold"].to_numpy()
    feat_cols = [
        c for c in table.columns if c not in ("scheme_id", "pattern", "fold", "incident", "owner")
    ]
    x = table.select(feat_cols).cast(pl.Float64).fill_null(np.nan).to_numpy()
    sig = shape(table, level)
    preds = {m: np.full(len(y), None, dtype=object) for m in METHODS}
    classes = [e["id"] for e in catalogue["entries"]]
    proba = np.full((len(y), len(classes)), np.nan)
    preds["rules"][detected] = rule_predict(sig[detected], catalogue)
    for k in (0, 1):
        train = detected & (fold == k)
        apply = detected & (fold != k)
        if not apply.any():
            continue
        if train.any():
            labels, counts = np.unique(y[train], return_counts=True)
            majority = labels[np.argmax(counts)]
        else:
            labels, majority = np.unique(y[detected]), np.unique(y[detected])[0]
        preds["majority"][apply] = majority
        preds["catalogue"][apply] = catalogue_predict(sig[apply], sig[train], catalogue)
        if len(labels) < 2:
            preds["attributor"][apply] = majority
            proba[apply] = 0.0
            proba[apply, classes.index(majority)] = 1.0
            continue
        model = LGBMClassifier(**ATTRIBUTOR, random_state=seed).fit(x[train], y[train])
        preds["attributor"][apply] = model.predict(x[apply])
        if proba_out is not None:
            p = np.asarray(model.predict_proba(x[apply]))
            proba[apply] = 0.0
            for j, c in enumerate(model.classes_):
                proba[np.nonzero(apply)[0], classes.index(c)] = p[:, j]
    if proba_out is not None:
        proba_out["classes"] = classes
        proba_out["p"] = proba
    return preds


# --------------------------------------------------------------------------- one seed
def run_seed_x6(
    paths: DatasetPaths,
    option: str,
    seed: int,
    progress: Callable[[str], None] | None = None,
    levels: tuple[str, ...] = tuple(LEVELS),
    keep_tables: bool = False,
) -> dict[str, Any]:
    """One seed of X6. ``levels`` and ``keep_tables`` serve the week-14 narrative: it needs
    only S2, and the per-scheme incident table with the attributor's probabilities."""
    t_start = time.perf_counter()
    catalogue = load_catalogue()
    r = run_seed(
        paths,
        option,
        seed,
        reps=1,
        window_reps=1,
        sweeps=True,
        audit=False,
        only=frozenset(LEVELS[lv] for lv in levels),
        return_scores=True,
        evaluate_configs=False,
    )
    t_levels = round(time.perf_counter() - t_start, 1)
    if progress:
        progress(f"seed {seed} levels: {t_levels:.0f} s")
    keys: pl.DataFrame = r["keys"]
    store = EvalStore(paths, option)
    plan = load_plan(paths)
    apm = store.accounts_per_member()
    feats = FeatureStore(paths, option, "member")
    pooled = FeatureStore(paths, option, "pooled")
    cols = feature_sets()["all"]
    lookback = int(feats.meta["neighbourhood"]["lookback_windows"])
    v0, v1 = (int(x) for x in store.meta["partition_windows"]["val"])
    part = store.partition("val")
    schemes = part.schemes
    sw = _within_delay(part.scheme_windows, schemes, DELAY_WINDOWS)

    alerts = {lv: _alerts(keys, r["scores"][LEVELS[lv]], apm, plan.window_hours) for lv in levels}
    any_alert = np.zeros(keys.height, dtype=bool)
    for a in alerts.values():
        any_alert |= a
    rows = np.nonzero(any_alert)[0]
    x_member = gather_rows(store, feats, rows, cols)
    x_pooled = gather_rows(store, pooled, rows, cols)
    pos_of = np.full(keys.height, -1)
    pos_of[rows] = np.arange(len(rows))
    edges = link_edges(
        paths.transactions, plan, v0, v1, lookback, touching=keys.filter(pl.Series(any_alert))
    )
    keyed = keys.with_row_index("row")
    base = schemes.select(
        "scheme_id",
        "pattern",
        pl.Series("fold", _halves(schemes["first_window"].to_numpy(), v0, v1)),
    )
    out: dict[str, Any] = {"seed": seed, "levels": {}}
    for lv in levels:
        alerted = keys.filter(pl.Series(alerts[lv]))
        inc = Linker(edges, lookback, lv != "S0")(alerted)
        inc = inc.join(keyed, on=KEYS).with_columns(
            pl.Series("pos", pos_of[inc.join(keyed, on=KEYS)["row"].to_numpy()])
        )
        feats_inc = incident_features(lv, inc, x_member, x_pooled, cols, seed)
        table = base.join(best_incident(sw, inc), on="scheme_id", how="left").join(
            feats_inc, on="incident", how="left"
        )
        proba: dict[str, Any] = {}
        preds = attribute(table, lv, seed, catalogue, proba if keep_tables else None)
        if keep_tables:
            out.setdefault("tables", {})[lv] = {"table": table, **proba}
        out["levels"][lv] = {
            "scheme_id": table["scheme_id"].to_list(),
            "pattern": table["pattern"].to_list(),
            "detected": table["incident"].is_not_null().to_list(),
            "predictions": {
                m: [None if p is None else str(p) for p in v] for m, v in preds.items()
            },
            "incidents": int(inc["incident"].n_unique()) if inc.height else 0,
            "features": len(feats_inc.columns) - 1,
        }
    out["seconds"] = {"levels": t_levels, "total": round(time.perf_counter() - t_start, 1)}
    if progress:
        progress(f"seed {seed} attribution: {out['seconds']['total'] - t_levels:.0f} s")
    return out


# --------------------------------------------------------------------------- statistics
def _ci(draws: np.ndarray, est: float) -> dict[str, float]:
    return {
        "estimate": float(est),
        "low": float(np.quantile(draws, 0.025)),
        "high": float(np.quantile(draws, 0.975)),
    }


def combine(per_seed: list[dict[str, Any]], reps: int = 1000) -> dict[str, Any]:
    """Per-scheme correctness averaged over seeds; scheme bootstrap, paired across configs."""
    first = per_seed[0]["levels"]["S0"]
    patterns = np.array(first["pattern"], dtype=object)
    n = len(patterns)
    classes = sorted(set(patterns.tolist()))
    rng = np.random.default_rng(0)
    idx = rng.integers(0, n, size=(reps, n)) if n else np.zeros((reps, 0), dtype=int)

    correct: dict[str, np.ndarray] = {}
    detected: dict[str, np.ndarray] = {}
    out: dict[str, Any] = {"schemes": n, "classes": classes, "levels": {}}
    for lv in LEVELS:
        det = np.mean(
            [np.array(s["levels"][lv]["detected"], dtype=float) for s in per_seed], axis=0
        )
        detected[lv] = det
        lv_out: dict[str, Any] = {"detected_share": float(det.mean()) if n else float("nan")}
        for m in METHODS:
            per = []
            f1s, det_acc = [], []
            for s in per_seed:
                L = s["levels"][lv]
                pred = np.array(L["predictions"][m], dtype=object)
                d = np.array(L["detected"], dtype=bool)
                ok = d & (pred == patterns)
                per.append(ok.astype(float))
                if d.any():
                    det_acc.append(float(ok[d].mean()))
                    f1s.append(
                        float(
                            f1_score(
                                patterns[d].astype(str),
                                pred[d].astype(str),
                                labels=classes,
                                average="macro",
                                zero_division=0,
                            )
                        )
                    )
            c = np.mean(per, axis=0)
            key = f"{lv}/{m}"
            correct[key] = c
            recall = {cl: float(c[patterns == cl].mean()) for cl in classes}
            lv_out[m] = {
                "accuracy": _ci(c[idx].mean(axis=1), c.mean()) if n else None,
                "accuracy_detected": float(np.mean(det_acc)) if det_acc else None,
                "macro_f1_detected": float(np.mean(f1s)) if f1s else None,
                "recall_by_pattern": recall,
            }
        out["levels"][lv] = lv_out

    def diff(a: str, b: str) -> dict[str, float]:
        d = correct[a] - correct[b]
        return _ci(d[idx].mean(axis=1), d.mean())

    comparisons = {
        f"{lv}-S0": diff(f"{lv}/attributor", "S0/attributor") for lv in LEVELS if lv != "S0"
    }
    for m in ("majority", "rules", "catalogue"):
        comparisons[f"S2 attributor-{m}"] = diff("S2/attributor", f"S2/{m}")
        comparisons[f"S0 attributor-{m}"] = diff("S0/attributor", f"S0/{m}")
    out["comparisons"] = comparisons
    h = comparisons
    out["H3a"] = {
        "S2_minus_S0": h["S2-S0"],
        "S2_above_majority": h["S2 attributor-majority"],
        "S2_above_rules": h["S2 attributor-rules"],
        "met_on_validation": bool(
            h["S2-S0"]["low"] > 0
            and h["S2 attributor-majority"]["low"] > 0
            and h["S2 attributor-rules"]["low"] > 0
        ),
    }
    stages = {e["id"]: e["stage"] for e in load_catalogue()["entries"]}
    stage_counts = {
        st: int(sum(stages.get(p) == st for p in patterns)) for st in set(stages.values())
    }
    top = max(stage_counts.values()) / n if n else 1.0
    out["stages"] = {"counts": stage_counts, "reported": bool(top <= 0.9)}
    return out


def run_x6(
    paths: DatasetPaths,
    option: str = "B8",
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    reps: int = 1000,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    with AnonPeak() as anon:
        per_seed = [run_seed_x6(paths, option, s, progress) for s in seeds]
        summary = combine(per_seed, reps)
    return {
        "dataset": paths.name,
        "option": option,
        "seeds": list(seeds),
        "levels": dict(LEVELS),
        "attributor": ATTRIBUTOR,
        "catalogue_version": load_catalogue()["version"],
        "summary": summary,
        "per_seed": per_seed,
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
    }


__all__ = [
    "LEVELS",
    "METHODS",
    "attribute",
    "best_incident",
    "catalogue_predict",
    "combine",
    "incident_features",
    "load_catalogue",
    "rule_predict",
    "run_x6",
    "shape",
]
