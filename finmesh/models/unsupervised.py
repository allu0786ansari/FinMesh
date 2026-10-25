"""Unsupervised floor (proposal Section 8.2): Isolation Forest and PCA reconstruction.

Fitted per member on a sample of its own training account-windows, without
labels. Features are signed-log transformed (heavy tails: counts, amounts)
and robustly standardised with the training sample's median and IQR; missing
values become the median (0 after standardising).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest

from finmesh.models.gbdt import matrix

PCA_VARIANCE = 0.95
IF_TREES = 200


def signed_log(x: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    return np.sign(x) * np.log1p(np.abs(x))


@dataclass
class RobustScaler:
    median: np.ndarray[Any, Any] = field(default_factory=lambda: np.zeros(0))
    scale: np.ndarray[Any, Any] = field(default_factory=lambda: np.ones(0))

    def fit(self, x: np.ndarray[Any, Any]) -> RobustScaler:
        z = signed_log(x)
        self.median = np.nan_to_num(np.nanmedian(z, axis=0))
        q75, q25 = np.nanpercentile(z, [75, 25], axis=0)
        iqr = np.nan_to_num(q75 - q25)
        std = np.nan_to_num(np.nanstd(z, axis=0))
        self.scale = np.where(iqr > 0, iqr, np.where(std > 0, std, 1.0))
        return self

    def transform(self, x: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        z = (signed_log(x) - self.median) / self.scale
        return np.asarray(np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0))


@dataclass
class Unsupervised:
    kind: str  # "iforest" or "pca"
    features: tuple[str, ...]
    seed: int
    scaler: RobustScaler = field(default_factory=RobustScaler)
    model: Any = None
    info: dict[str, Any] = field(default_factory=dict)

    def fit(self, frame: pl.DataFrame) -> Unsupervised:
        x = matrix(frame, self.features).astype(np.float64)
        z = self.scaler.fit(x).transform(x)
        if self.kind == "iforest":
            # Fitting is seeded; scoring in parallel does not change the scores.
            self.model = IsolationForest(
                n_estimators=IF_TREES, random_state=self.seed, n_jobs=-1
            ).fit(z)
            self.info = {"rows": len(z), "trees": IF_TREES}
        elif self.kind == "pca":
            self.model = PCA(n_components=PCA_VARIANCE, svd_solver="full", random_state=self.seed)
            self.model.fit(z)
            self.info = {"rows": len(z), "components": int(self.model.n_components_)}
        else:
            raise ValueError(self.kind)
        return self

    def score(self, frame: pl.DataFrame) -> np.ndarray[Any, Any]:
        """Higher = more anomalous."""
        z = self.scaler.transform(matrix(frame, self.features).astype(np.float64))
        if self.kind == "iforest":
            return -np.asarray(self.model.score_samples(z))
        recon = self.model.inverse_transform(self.model.transform(z))
        return np.asarray(((z - recon) ** 2).sum(axis=1))
