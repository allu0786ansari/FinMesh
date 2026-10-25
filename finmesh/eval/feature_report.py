"""Single-feature signal on validation: a first look and a leakage smoke test.

Each feature is used alone as a score (missing values rank lowest). AUROC is
reported as computed; AUPRC is reported in the feature's better orientation
(high or low values first), chosen on the same data, so it is descriptive,
not an estimate of model performance.

A single behavioural feature that almost separates the classes on AMLworld
is more likely a leak than a discovery: anything with oriented AUROC of at
least 0.95 or AUPRC of at least 0.5 is flagged for inspection before week 5.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from finmesh.eval.guard import KEY_COLUMNS
from finmesh.eval.metrics import RankedScores
from finmesh.eval.sealed import EvalStore
from finmesh.features.build import FeatureStore
from finmesh.reporting import table

LEAK_AUROC = 0.95
LEAK_AUPRC = 0.5


def feature_signal(
    store: EvalStore, features: FeatureStore, partition: str = "val"
) -> dict[str, Any]:
    """One feature column in memory at a time: about 1 GB at 9 M account-windows."""
    labels = store.partition(partition).labels.frame
    keys = features.partition(partition, columns=[]).frame
    if keys.height != labels.height or not all(
        labels[c].equals(keys[c], check_dtypes=False) for c in KEY_COLUMNS
    ):
        raise RuntimeError(
            "feature rows do not line up with the labels; rebuild both with "
            "`finmesh labels` then `finmesh features`"
        )
    del keys
    keep = ~labels["masked"].to_numpy()
    y = labels["label"].to_numpy()[keep].astype(np.int8)
    del labels
    positives = int(y.sum())
    is_pos = y == 1
    rows: list[dict[str, Any]] = []
    for spec in features.schema.features:
        name = spec["name"]
        col = features.partition(partition, columns=[name]).frame[name]
        values = col.cast(pl.Float64).to_numpy()[keep]
        del col
        present = ~np.isnan(values)
        lowest = float(np.nanmin(values)) - 1.0 if present.any() else 0.0
        s = np.where(present, values, lowest)
        ap_hi, auc = RankedScores(y, s).stats()
        ap_lo, _ = RankedScores(y, -s).stats()
        high_first = auc >= 0.5
        oriented_auc = auc if high_first else 1.0 - auc
        ap = ap_hi if high_first else ap_lo
        rows.append(
            {
                "feature": name,
                "family": spec["family"],
                "present": float(present.mean()) if len(present) else 0.0,
                "mean_positive": _nanmean(values[is_pos]),
                "mean_negative": _nanmean(values[~is_pos]),
                "auroc": auc,
                "direction": "high" if high_first else "low",
                "auprc": ap,
                "lift": ap / (positives / len(y)) if positives else None,
                "flag": oriented_auc >= LEAK_AUROC or ap >= LEAK_AUPRC,
            }
        )
        del values, s
    rows.sort(key=lambda r: -float(r["auprc"] or 0.0))
    return {
        "partition": partition,
        "account_windows": len(y),
        "positives": positives,
        "prevalence": positives / len(y) if len(y) else None,
        "features": rows,
        "flagged": [r["feature"] for r in rows if r["flag"]],
    }


def _nanmean(a: np.ndarray[Any, Any]) -> float | None:
    a = a[~np.isnan(a)]
    return float(a.mean()) if a.size else None


def render_feature_signal(dataset: str, option: str, result: dict[str, Any]) -> str:
    lines = [
        f"# Single-feature signal · {dataset}",
        "",
        f"Federation {option}, feature schema v1, {result['partition']} partition: "
        f"{result['account_windows']:,} account-windows, {result['positives']:,} positive "
        f"(prevalence {result['prevalence']:.4f}). Each feature alone ranks the "
        "account-windows; AUPRC uses the better direction, chosen on these same rows, so the "
        "table is descriptive. Lift = AUPRC / prevalence.",
        "",
        "**Leakage check:** "
        + (
            "no feature reaches AUROC 0.95 or AUPRC 0.5 on its own."
            if not result["flagged"]
            else f"**inspect before week 5:** {', '.join(result['flagged'])}."
        ),
        "",
    ]
    cols = [
        ("feature", "Feature"),
        ("family", "Family"),
        ("present", "Present"),
        ("mean_positive", "Mean (positive)"),
        ("mean_negative", "Mean (negative)"),
        ("auroc", "AUROC"),
        ("direction", "Better"),
        ("auprc", "AUPRC"),
        ("lift", "Lift"),
    ]
    lines.append(table(result["features"], cols))
    return "\n".join(lines) + "\n"
