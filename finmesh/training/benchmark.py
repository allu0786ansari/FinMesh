"""A25 P6: our detector on AMLworld's published benchmark split (transaction level).

Dataset: ``<source>-FULL`` (``finmesh.data.benchmark_split``): every transaction, split by
day 60/20/20 as in the benchmark code, with our 6 h windows and pooled-view features built
by the usual pipeline. The task is the benchmark's: is each transaction laundering?
Metric: minority-class F1 on test, at the threshold that maximises F1 on validation;
5 seeds; mean and standard deviation, as published.

Models (fixed in the A25 plan):

- **A, pooled detector**: our LightGBM on the 47 account-window features of the pooled
  view (the oracle's model, trained on the benchmark's train days with our account-window
  labels); a transaction scores the larger of its sender's and receiver's account-window
  scores in the transaction's window.
- **B, transaction model**: a LightGBM on the transaction's own fields (amounts, currencies,
  payment format, same bank, self transfer, hour, weekday) plus both accounts' 47 features,
  trained on train-day transactions with transaction labels (negatives subsampled and
  weighted), early stopping on the last part of the training period.

Adequacy rule (fixed in the plan): model A's **validation** F1 against published
LightGBM + graph features; more than 5 points below on HI-Medium or LI-Medium triggers the
stronger-detector track. Memory: one partition's transactions at a time, features read per
day, scores kept as float32 arrays.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import lightgbm as lgb
import numpy as np
import polars as pl

from finmesh.data.benchmark_split import is_benchmark, source_of
from finmesh.data.lowmem import hashed_key
from finmesh.data.splits import partition_expr, window_index_expr
from finmesh.eval.sealed import EvalStore
from finmesh.eval.split_io import load_plan
from finmesh.features.build import FeatureStore
from finmesh.models.gbdt import EARLY_STOPPING, GBDT, MAX_ROUNDS, PARAMS
from finmesh.paths import DatasetPaths
from finmesh.training.baselines import feature_sets
from finmesh.training.data import NEGATIVE_RATE, SAMPLE_SALT, training_rows, training_windows

SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
OWN: tuple[str, ...] = (
    "log_amount_paid",
    "log_amount_received",
    "payment_currency_code",
    "receiving_currency_code",
    "payment_format_code",
    "cross_currency",
    "same_bank",
    "self_transfer",
    "hour",
    "weekday",
)
CATEGORICAL = ("payment_currency_code", "receiving_currency_code", "payment_format_code")
ADEQUACY_POINTS = 5.0
ADEQUACY_DATASETS = ("HI-Medium", "LI-Medium")

# Egressy et al., AAAI 2024 (minority-class F1, %, test).
PUBLISHED: dict[str, dict[str, float]] = {
    "LightGBM + graph features": {
        "HI-Small": 62.86,
        "LI-Small": 20.83,
        "HI-Medium": 59.48,
        "LI-Medium": 20.85,
    },
    "XGBoost + graph features": {
        "HI-Small": 63.23,
        "LI-Small": 27.30,
        "HI-Medium": 65.70,
        "LI-Medium": 28.16,
    },
    "Multi-PNA + EU": {
        "HI-Small": 68.16,
        "LI-Small": 33.07,
        "HI-Medium": 66.48,
        "LI-Medium": 36.07,
    },
}


# --------------------------------------------------------------------------- inputs
def _codes(paths: DatasetPaths) -> dict[str, list[str]]:
    lf = pl.scan_parquet(paths.transactions)
    cur = (
        pl.concat(
            [
                lf.select(pl.col("payment_currency").alias("c")),
                lf.select(pl.col("receiving_currency").alias("c")),
            ]
        )
        .unique()
        .collect(engine="streaming")["c"]
    )
    fmt = lf.select("payment_format").unique().collect(engine="streaming")["payment_format"]
    return {
        "currency": sorted(str(c) for c in cur.drop_nulls()),
        "format": sorted(str(f) for f in fmt.drop_nulls()),
    }


def transactions(paths: DatasetPaths, partition: str, codes: dict[str, list[str]]) -> pl.DataFrame:
    """One benchmark partition's transactions: keys, own fields and the target."""
    plan = load_plan(paths)
    cur = {c: i for i, c in enumerate(codes["currency"])}
    fmt = {f: i for i, f in enumerate(codes["format"])}
    ts = pl.col("timestamp")
    return (
        pl.scan_parquet(paths.transactions)
        .filter(partition_expr(plan).cast(pl.String) == partition)
        .select(
            "tx_id",
            window_index_expr(plan).alias("window"),
            hashed_key("src_key").alias("src"),
            hashed_key("dst_key").alias("dst"),
            pl.col("amount_paid").log1p().cast(pl.Float32).alias("log_amount_paid"),
            pl.col("amount_received").log1p().cast(pl.Float32).alias("log_amount_received"),
            pl.col("payment_currency")
            .replace_strict(cur, default=-1, return_dtype=pl.Int16)
            .alias("payment_currency_code"),
            pl.col("receiving_currency")
            .replace_strict(cur, default=-1, return_dtype=pl.Int16)
            .alias("receiving_currency_code"),
            pl.col("payment_format")
            .replace_strict(fmt, default=-1, return_dtype=pl.Int16)
            .alias("payment_format_code"),
            (pl.col("payment_currency") != pl.col("receiving_currency"))
            .cast(pl.Int8)
            .alias("cross_currency"),
            (pl.col("from_bank") == pl.col("to_bank")).cast(pl.Int8).alias("same_bank"),
            (pl.col("src_key") == pl.col("dst_key")).cast(pl.Int8).alias("self_transfer"),
            ts.dt.hour().cast(pl.Int8).alias("hour"),
            ts.dt.weekday().cast(pl.Int8).alias("weekday"),
            pl.col("is_laundering").cast(pl.Int8).alias("y"),
        )
        .sort("window", "tx_id")
        .collect(engine="streaming")
    )


def _features(
    pooled: FeatureStore, partition: str, w0: int, w1: int, cols: tuple[str, ...]
) -> pl.DataFrame:
    files = sorted(pooled.layout.partition_dir(partition).glob("feat_*.parquet"))
    return (
        pl.scan_parquet(files)
        .filter(pl.col("window").is_between(w0, w1))
        .select("account", "window", *cols)
        .collect()
    )


def _attach(tx: pl.DataFrame, feats: pl.DataFrame, cols: tuple[str, ...]) -> pl.DataFrame:
    """Sender's and receiver's account-window features (and scores) on each transaction."""
    out = tx
    for side in ("src", "dst"):
        f = feats.rename({c: f"{side}_{c}" for c in cols}).rename({"account": side})
        out = out.join(f, on=[side, "window"], how="left", maintain_order="left")
    return out


def _tx_columns(cols: tuple[str, ...]) -> tuple[str, ...]:
    return (*OWN, *(f"src_{c}" for c in cols), *(f"dst_{c}" for c in cols))


def _matrix(frame: pl.DataFrame, names: tuple[str, ...]) -> np.ndarray[Any, Any]:
    return frame.select(pl.col(list(names)).cast(pl.Float32)).to_numpy().astype(np.float32)


def _days(tx: pl.DataFrame, per_day: int) -> list[tuple[int, int]]:
    ws = tx["window"].unique().sort().to_list()
    days = sorted({int(w) // per_day for w in ws})
    return [(d * per_day, d * per_day + per_day - 1) for d in days]


# --------------------------------------------------------------------------- metrics
def best_f1(y: np.ndarray[Any, Any], s: np.ndarray[Any, Any]) -> tuple[float, float]:
    """(F1, threshold) maximising F1 over every distinct score threshold."""
    order = np.argsort(-s, kind="stable")
    ys, ss = y[order].astype(np.int64), s[order]
    tp = np.cumsum(ys)
    k = np.arange(1, len(ys) + 1)
    last = np.r_[ss[1:] != ss[:-1], True]  # cut only between distinct scores
    tp, k, ss = tp[last], k[last], ss[last]
    pos = int(ys.sum())
    if pos == 0 or len(tp) == 0:
        return 0.0, float("inf")
    f1 = 2 * tp / (k + pos)
    i = int(np.argmax(f1))
    return float(f1[i]), float(ss[i])


def f1_at(y: np.ndarray[Any, Any], s: np.ndarray[Any, Any], thr: float) -> float:
    pred = s >= thr
    tp = int((pred & (y == 1)).sum())
    den = int(pred.sum()) + int((y == 1).sum())
    return 2 * tp / den if den else 0.0


def auprc(y: np.ndarray[Any, Any], s: np.ndarray[Any, Any]) -> float:
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(y, s)) if y.any() else 0.0


# --------------------------------------------------------------------------- run
def run_benchmark(
    paths: DatasetPaths,
    option: str = "B8",
    seeds: tuple[int, ...] = SEEDS,
    negative_rate: float = NEGATIVE_RATE,
    progress: Callable[[str], None] = lambda _m: None,
) -> dict[str, Any]:
    if not is_benchmark(paths.name):
        raise ValueError(
            f"{paths.name} is not a benchmark dataset; run `finmesh benchmark-dataset`"
        )
    t_start = time.perf_counter()
    plan = load_plan(paths)
    per_day = 24 // plan.window_hours
    store = EvalStore(paths, option)
    pooled = FeatureStore(paths, option, "pooled")
    windows = training_windows(store, pooled)
    cols = feature_sets()["all"]
    names = _tx_columns(cols)
    codes = _codes(paths)
    seconds: dict[str, float] = {}

    # Model A: the pooled detector (our oracle's model), one per seed.
    t0 = time.perf_counter()
    model_a = {}
    for s in seeds:
        fit, stop = training_rows(store, pooled, cols, windows, s)
        model_a[s] = GBDT(cols, s).fit(fit.x, fit.y, fit.w, stop.x, stop.y, stop.w)
        del fit, stop
        progress(f"model A seed {s}: {model_a[s].info['rounds']} rounds")
    seconds["model_a"] = round(time.perf_counter() - t0, 1)

    # Model B: transaction rows of the training days (after the burn-in).
    t0 = time.perf_counter()
    tx = transactions(paths, "train", codes)
    parts: dict[str, list[Any]] = {"fit": [], "stop": []}
    for w0, w1 in _days(tx, per_day):
        if w1 < windows.burn_in:
            continue
        day = tx.filter(pl.col("window").is_between(max(w0, windows.burn_in), w1))
        u = pl.col("tx_id").hash(seed=SAMPLE_SALT).cast(pl.Float64) / 2.0**64
        day = day.filter((pl.col("y") == 1) | (u < negative_rate))
        if day.is_empty():
            continue
        day = _attach(day, _features(pooled, "train", w0, w1, cols), cols)
        yy = day["y"].to_numpy().astype(np.int8)
        late = day["window"].to_numpy() >= windows.stop_from
        x = _matrix(day, names)
        w = np.where(yy == 1, 1.0, 1.0 / negative_rate).astype(np.float32)
        for k, mask in (("fit", ~late), ("stop", late)):
            parts[k].append((x[mask], yy[mask], w[mask]))
    del tx
    xb, yb, wb = (np.concatenate(a) for a in zip(*parts["fit"], strict=True))
    xs, ys, ws = (np.concatenate(a) for a in zip(*parts["stop"], strict=True))
    del parts
    model_b = {}
    info_b = {}
    for s in seeds:
        params = {**PARAMS, "seed": s}
        train = lgb.Dataset(
            xb,
            yb,
            weight=wb,
            feature_name=list(names),
            categorical_feature=list(CATEGORICAL),
            free_raw_data=False,
        )
        stop_ds = lgb.Dataset(xs, ys, weight=ws, reference=train)
        model_b[s] = lgb.train(
            params,
            train,
            num_boost_round=MAX_ROUNDS,
            valid_sets=[stop_ds],
            callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False)],
        )
        info_b[s] = {
            "rounds": int(model_b[s].best_iteration or model_b[s].current_iteration()),
            "train_rows": len(yb),
            "train_positives": int(yb.sum()),
        }
        progress(f"model B seed {s}: {info_b[s]['rounds']} rounds")
    del xb, yb, wb, xs, ys, ws
    seconds["model_b"] = round(time.perf_counter() - t0, 1)

    # Score validation and test, day by day.
    scored: dict[str, dict[str, Any]] = {}
    for part in ("val", "test"):
        t0 = time.perf_counter()
        tx = transactions(paths, part, codes)
        y_parts, a_parts, b_parts = [], [], []
        missing = 0
        for w0, w1 in _days(tx, per_day):
            day = tx.filter(pl.col("window").is_between(w0, w1))
            feats = _features(pooled, part, w0, w1, cols)
            fa = feats.select("account", "window")
            for s in seeds:
                fa = fa.with_columns(pl.Series(f"a{s}", model_a[s].score(feats).astype(np.float32)))
            d = _attach(day, feats, cols)
            for side in ("src", "dst"):
                d = d.join(
                    fa.rename({"account": side, **{f"a{s}": f"{side}_a{s}" for s in seeds}}),
                    on=[side, "window"],
                    how="left",
                    maintain_order="left",
                )
            missing += d[f"src_{cols[0]}"].null_count() + d[f"dst_{cols[0]}"].null_count()
            x = _matrix(d, names)
            y_parts.append(d["y"].to_numpy().astype(np.int8))
            a_parts.append(
                np.column_stack(
                    [
                        np.fmax(
                            d[f"src_a{s}"].fill_null(np.nan).to_numpy(),
                            d[f"dst_a{s}"].fill_null(np.nan).to_numpy(),
                        )
                        for s in seeds
                    ]
                ).astype(np.float32)
            )
            b_parts.append(
                np.column_stack(
                    [model_b[s].predict(x, num_iteration=model_b[s].best_iteration) for s in seeds]
                ).astype(np.float32)
            )
            del day, feats, fa, d, x
        a = np.nan_to_num(np.concatenate(a_parts), nan=0.0)
        scored[part] = {
            "y": np.concatenate(y_parts),
            "A": a,
            "B": np.concatenate(b_parts),
            "rows": int(tx.height),
            "positives": int(tx["y"].sum()),
            "missing_account_windows": missing,
        }
        del tx
        seconds[f"score_{part}"] = round(time.perf_counter() - t0, 1)
        progress(f"{part}: {scored[part]['rows']:,} transactions scored")

    models: dict[str, Any] = {}
    for m in ("A", "B"):
        rows = []
        for i, s in enumerate(seeds):
            yv, sv = scored["val"]["y"], scored["val"][m][:, i]
            yt, st = scored["test"]["y"], scored["test"][m][:, i]
            f1v, thr = best_f1(yv, sv)
            rows.append(
                {
                    "seed": s,
                    "val_f1": 100 * f1v,
                    "threshold": thr,
                    "test_f1": 100 * f1_at(yt, st, thr),
                    "test_f1_oracle_threshold": 100 * best_f1(yt, st)[0],
                    "val_auprc": auprc(yv, sv),
                    "test_auprc": auprc(yt, st),
                }
            )
        models[m] = {"per_seed": rows, **_mean_sd(rows)}
    source = source_of(paths.name)
    lgbm = PUBLISHED["LightGBM + graph features"].get(source)
    gap = None if lgbm is None else models["A"]["val_f1_mean"] - lgbm
    return {
        "dataset": paths.name,
        "source": source,
        "option": option,
        "seeds": list(seeds),
        "split": {p.name: [str(p.start), str(p.end)] for p in plan.periods if p.name != "gap"},
        "rows": {
            p: {k: scored[p][k] for k in ("rows", "positives", "missing_account_windows")}
            for p in ("val", "test")
        },
        "negative_rate": negative_rate,
        "model_a": {str(s): m.info for s, m in model_a.items()},
        "model_b": {str(s): v for s, v in info_b.items()},
        "models": models,
        "published": {k: v.get(source) for k, v in PUBLISHED.items()},
        "adequacy": {
            "reference": "LightGBM + graph features",
            "reference_f1": lgbm,
            "model_a_val_f1": models["A"]["val_f1_mean"],
            "gap_points": gap,
            "applies": source in ADEQUACY_DATASETS,
            "triggered": bool(
                gap is not None and source in ADEQUACY_DATASETS and gap < -ADEQUACY_POINTS
            ),
        },
        "seconds": {**seconds, "total": round(time.perf_counter() - t_start, 1)},
    }


def _mean_sd(rows: list[dict[str, Any]]) -> dict[str, float]:
    out = {}
    for k in ("val_f1", "test_f1", "test_f1_oracle_threshold", "val_auprc", "test_auprc"):
        v = np.array([r[k] for r in rows], dtype=float)
        out[f"{k}_mean"] = float(v.mean())
        out[f"{k}_sd"] = float(v.std(ddof=1)) if len(v) > 1 else 0.0
    return out


# --------------------------------------------------------------------------- report
def render(r: dict[str, Any]) -> str:
    def ms(m: dict[str, Any], k: str) -> str:
        return f"{m[f'{k}_mean']:.2f} ± {m[f'{k}_sd']:.2f}"

    a, b = r["models"]["A"], r["models"]["B"]
    ad = r["adequacy"]
    lines = [
        f"# Benchmark anchor (A25 P6) · {r['source']}",
        "",
        "AMLworld's published split: every transaction, by day 60/20/20 "
        f"(train {r['split']['train'][0]} – {r['split']['train'][1]}, validation "
        f"{r['split']['val'][0]} – {r['split']['val'][1]}, test {r['split']['test'][0]} – "
        f"{r['split']['test'][1]}). Minority-class F1 (%) on test at the threshold that "
        f"maximises validation F1; seeds {r['seeds']}, mean ± sd.",
        "",
        "| Model | Test F1 | Validation F1 | Test AUPRC |",
        "| --- | --- | --- | --- |",
        f"| A · our pooled detector (account-window LightGBM, max of the two accounts) | "
        f"{ms(a, 'test_f1')} | {ms(a, 'val_f1')} | {a['test_auprc_mean']:.3f} |",
        f"| B · transaction LightGBM (own fields + both accounts' features) | "
        f"{ms(b, 'test_f1')} | {ms(b, 'val_f1')} | {b['test_auprc_mean']:.3f} |",
    ]
    for k, v in r["published"].items():
        if v is not None:
            lines.append(f"| {k} (Egressy et al., AAAI 2024) | {v:.2f} | — | — |")
    lines += [
        "",
        f"Test: {r['rows']['test']['rows']:,} transactions, {r['rows']['test']['positives']:,} "
        f"laundering. Validation: {r['rows']['val']['rows']:,}, "
        f"{r['rows']['val']['positives']:,}. Account-windows missing: "
        f"{sum(r['rows'][p]['missing_account_windows'] for p in ('val', 'test'))}.",
        "",
    ]
    if ad["reference_f1"] is not None:
        verdict = (
            "**triggered**: the stronger-detector track (S0+, S2+, oracle+) is developed on "
            "validation and added to the Large confirmation"
            if ad["triggered"]
            else (
                "not triggered"
                if ad["applies"]
                else "reported only (the rule reads the Medium sets)"
            )
        )
        lines += [
            f"Adequacy rule: model A's validation F1 {ad['model_a_val_f1']:.2f} vs "
            f"{ad['reference']} {ad['reference_f1']:.2f} → gap {ad['gap_points']:+.2f} points "
            f"(threshold −{ADEQUACY_POINTS:g}): {verdict}.",
            "",
        ]
    return "\n".join(lines)


def render_table(results: list[dict[str, Any]]) -> str:
    order = ("HI-Small", "LI-Small", "HI-Medium", "LI-Medium")
    by = {r["source"]: r for r in results}
    cols = [s for s in order if s in by] + [s for s in by if s not in order]

    def cell(src: str, m: str) -> str:
        if src not in by:
            return "—"
        x = by[src]["models"][m]
        return f"{x['test_f1_mean']:.2f} ± {x['test_f1_sd']:.2f}"

    lines = [
        "# Benchmark anchor (A25 P6): minority-class F1 (%), AMLworld split",
        "",
        "| Model | " + " | ".join(cols) + " |",
        "| --- |" + " --- |" * len(cols),
        "| A · our pooled detector | " + " | ".join(cell(c, "A") for c in cols) + " |",
        "| B · transaction LightGBM + our features | "
        + " | ".join(cell(c, "B") for c in cols)
        + " |",
    ]
    for k, v in PUBLISHED.items():
        lines.append(
            f"| {k} (published) | "
            + " | ".join(f"{v[c]:.2f}" if c in v else "—" for c in cols)
            + " |"
        )
    lines += ["", "Adequacy (model A, validation F1 vs LightGBM + graph features):", ""]
    for c in cols:
        ad = by[c]["adequacy"]
        if ad["gap_points"] is not None:
            lines.append(
                f"- {c}: {ad['gap_points']:+.2f} points"
                + (" — **triggered**" if ad["triggered"] else "")
            )
    return "\n".join(lines) + "\n"


__all__ = ["PUBLISHED", "best_f1", "f1_at", "render", "render_table", "run_benchmark"]
