"""Training and scoring data: labels and features slice by slice, row for row.

This package is where labels meet features, so it sits outside the label-free
packages (CC1): it builds arrays for ``finmesh.models``, which never sees a
label column, and collects scores in the label files' row order so the
harness attaches them without a join.

Training rows (preregistered, docs/protocol/preregistration.md):

* training partition only, from the first window with complete history
  (``history_complete_from_window``; the burn-in is excluded);
* the last :data:`STOP_SHARE` of those windows are held out for early
  stopping and for fitting FPR thresholds (out of sample for the model);
* masked rows never train;
* every positive is kept; negatives are kept with probability
  :data:`NEGATIVE_RATE`, drawn by a fixed hash of (account, window), and
  weighted by its inverse.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl

from finmesh.eval.guard import KEY_COLUMNS
from finmesh.eval.sealed import EvalStore, label_variant
from finmesh.features.build import FeatureStore
from finmesh.models.gbdt import matrix

NEGATIVE_RATE = 0.1
STOP_SHARE = 0.2
SAMPLE_SALT = 0x5A4D504C45000000


@dataclass(frozen=True)
class Windows:
    burn_in: int
    stop_from: int
    train_last: int

    def to_dict(self) -> dict[str, int]:
        return {"burn_in": self.burn_in, "stop_from": self.stop_from, "train_last": self.train_last}


def training_windows(store: EvalStore, features: FeatureStore) -> Windows:
    first, last = store.meta["partition_windows"]["train"]
    burn_in = max(int(first), int(features.meta.get("history_complete_from_window", 0)))
    span = int(last) - burn_in + 1
    if span < 2:
        raise ValueError("the training period is shorter than the burn-in")
    stop_from = int(last) - max(1, round(span * STOP_SHARE)) + 1
    return Windows(burn_in, stop_from, int(last))


def slices(
    store: EvalStore, features: FeatureStore, partition: str, variant: str = "primary"
) -> Iterator[tuple[pl.DataFrame, pl.DataFrame]]:
    """(labels, features) per slice, checked to line up row for row."""
    lab_dir = store.layout.partition_dir(partition)
    feat_dir = features.layout.partition_dir(partition)
    lab_files = sorted(lab_dir.glob("universe_*.parquet"))
    feat_files = sorted(feat_dir.glob("feat_*.parquet"))
    if [f.stem.split("_")[-1] for f in lab_files] != [f.stem.split("_")[-1] for f in feat_files]:
        raise RuntimeError("label and feature slices differ; rebuild labels, then features")
    for lf, ff in zip(lab_files, feat_files, strict=True):
        lab = label_variant(pl.read_parquet(lf), variant)
        feat = pl.read_parquet(ff)
        if lab.height != feat.height or not all(
            lab[c].equals(feat[c], check_dtypes=False) for c in KEY_COLUMNS
        ):
            raise RuntimeError(f"{ff.name} does not line up with {lf.name}; rebuild features")
        yield lab, feat


def _keep_negative(frame: pl.DataFrame, rate: float, seed: int) -> pl.Series:
    u = pl.struct("account", "window").hash(seed=SAMPLE_SALT + seed).cast(pl.Float64) / 2.0**64
    return frame.select(u < rate).to_series()


@dataclass
class Rows:
    x: np.ndarray[Any, Any]
    y: np.ndarray[Any, Any]
    w: np.ndarray[Any, Any]
    member: np.ndarray[Any, Any]


def training_rows(
    store: EvalStore,
    features: FeatureStore,
    columns: tuple[str, ...],
    windows: Windows,
    seed: int,
    variant: str = "primary",
    rate: float = NEGATIVE_RATE,
) -> tuple[Rows, Rows]:
    """(fit rows, early-stopping rows), negatives subsampled and weighted."""
    parts: dict[str, list[tuple[Any, ...]]] = {"fit": [], "stop": []}
    for lab, feat in slices(store, features, "train", variant):
        y = lab["label"].cast(pl.Int8)
        usable = (~lab["masked"]) & (lab["window"] >= windows.burn_in)
        keep = usable & ((y == 1) | _keep_negative(lab, rate, seed))
        stop = lab["window"] >= windows.stop_from
        for name, mask in (("fit", keep & ~stop), ("stop", keep & stop)):
            sub_lab, sub_feat = lab.filter(mask), feat.filter(mask)
            yy = sub_lab["label"].to_numpy().astype(np.int8)
            parts[name].append(
                (
                    matrix(sub_feat, columns),
                    yy,
                    np.where(yy == 1, 1.0, 1.0 / rate),
                    sub_lab["member"].to_numpy(),
                )
            )
    out = []
    for name in ("fit", "stop"):
        xs, ys, ws, ms = zip(*parts[name], strict=True)
        out.append(
            Rows(np.concatenate(xs), np.concatenate(ys), np.concatenate(ws), np.concatenate(ms))
        )
    return out[0], out[1]


def sample_rows(
    features: FeatureStore, columns: tuple[str, ...], windows: Windows, rows: int, seed: int
) -> pl.DataFrame:
    """Label-free sample of training account-windows after the burn-in (unsupervised models)."""
    meta_rows = int(features.meta["rows"]["train"])
    rate = min(1.0, rows / max(meta_rows, 1))
    picked = []
    for f in sorted(features.layout.partition_dir("train").glob("feat_*.parquet")):
        frame = pl.read_parquet(f, columns=[*KEY_COLUMNS, *columns])
        mask = (frame["window"] >= windows.burn_in) & _keep_negative(frame, rate, seed + 1)
        picked.append(frame.filter(mask))
    return pl.concat(picked)
