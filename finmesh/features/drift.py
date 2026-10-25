"""Feature drift between partitions (label-free).

Population stability index (PSI) of each feature from train to a later
partition, on deciles of the training distribution, plus the share of
non-zero values in each. A feature that fires in training but never later
(for example a payment format that only occurs at the start of the month)
can only teach a model a pattern it will never see again.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from finmesh.features.build import FeatureStore

PSI_FLAG = 0.25  # conventional "large shift" threshold
SAMPLE_ROWS = 2_000_000
EPS = 1e-4


def _sample(values: np.ndarray[Any, Any], rows: int) -> np.ndarray[Any, Any]:
    if values.size <= rows:
        return values
    step = values.size / rows
    return values[(np.arange(rows) * step).astype(np.int64)]  # deterministic, spread evenly


def psi(reference: np.ndarray[Any, Any], later: np.ndarray[Any, Any]) -> float:
    """PSI on reference deciles; missing values form their own bin."""
    ref_nan, new_nan = np.isnan(reference), np.isnan(later)
    ref, new = reference[~ref_nan], later[~new_nan]
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, 11))) if ref.size else np.array([0.0])
    inner = edges[1:-1]

    def shares(x: np.ndarray[Any, Any], missing: int, total: int) -> np.ndarray[Any, Any]:
        counts = np.bincount(np.searchsorted(inner, x, side="right"), minlength=inner.size + 1)
        out = np.append(counts, missing).astype(np.float64)
        return np.maximum(out / max(total, 1), EPS)

    p = shares(ref, int(ref_nan.sum()), reference.size)
    q = shares(new, int(new_nan.sum()), later.size)
    return float(np.sum((q - p) * np.log(q / p)))


def feature_drift(store: FeatureStore, later: str = "val") -> list[dict[str, Any]]:
    """Train (after the burn-in, as models will see it) against ``later``."""
    burn_in = int(store.meta.get("history_complete_from_window", 0))
    windows = store.partition("train", columns=[]).frame["window"].to_numpy()
    kept = windows >= burn_in
    rows: list[dict[str, Any]] = []
    for name in store.schema.names:
        col = store.partition("train", columns=[name]).frame[name]
        train = col.cast(pl.Float64).to_numpy()[kept]
        new = store.partition(later, columns=[name]).frame[name].cast(pl.Float64).to_numpy()
        train_s = _sample(train, SAMPLE_ROWS)
        nz_train = float(np.nanmean(train_s != 0)) if train_s.size else 0.0
        nz_new = float(np.nanmean(new != 0)) if new.size else 0.0
        value = psi(train_s, new)
        absent = nz_train >= 1e-3 and nz_new == 0.0
        rows.append(
            {
                "feature": name,
                "nonzero_train": nz_train,
                f"nonzero_{later}": nz_new,
                "psi": value,
                "flag": "absent later" if absent else ("drift" if value > PSI_FLAG else ""),
            }
        )
        del train, new, train_s
    rows.sort(key=lambda r: -float(r["psi"]))
    return rows
