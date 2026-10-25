"""Local autoencoder (proposal Section 8.2): the label-free complement.

A small MLP (features -> 24 -> 8 -> 24 -> features) trained per member to
reconstruct its own robust-scaled account-windows. Its per-feature squared
reconstruction error is the **deviation vector**: the evidence record carries
the three most deviating features, with direction and a magnitude bucket. The
8-unit bottleneck is the window **embedding** that S4 shares (week 7).

Implemented with scikit-learn's MLPRegressor (multi-output regression of the
input onto itself), so no deep-learning framework is needed before week 10.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor

from finmesh.models.gbdt import matrix
from finmesh.models.unsupervised import RobustScaler

HIDDEN = (24, 8, 24)
MAX_ITER = 60


@dataclass
class Autoencoder:
    features: tuple[str, ...]
    seed: int
    scaler: RobustScaler = field(default_factory=RobustScaler)
    model: MLPRegressor | None = None
    info: dict[str, Any] = field(default_factory=dict)

    def fit(self, frame: pl.DataFrame) -> Autoencoder:
        x = matrix(frame, self.features).astype(np.float64)
        z = np.clip(self.scaler.fit(x).transform(x), -10.0, 10.0)
        with warnings.catch_warnings():
            # A fixed iteration cap is part of the design; the count is recorded in info.
            warnings.simplefilter("ignore", ConvergenceWarning)
            self.model = MLPRegressor(
                hidden_layer_sizes=HIDDEN,
                activation="relu",
                max_iter=MAX_ITER,
                early_stopping=True,
                random_state=self.seed,
            ).fit(z, z)
        recon = self.model.predict(z)
        self.info = {
            "rows": len(z),
            "iterations": int(self.model.n_iter_),
            "train_mse": float(np.mean((z - recon) ** 2)),
        }
        return self

    def _scaled(self, frame: pl.DataFrame) -> np.ndarray[Any, Any]:
        z = self.scaler.transform(matrix(frame, self.features).astype(np.float64))
        return np.asarray(np.clip(z, -10.0, 10.0))

    def deviations(self, frame: pl.DataFrame) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
        """(squared error, signed difference) per row and feature."""
        if self.model is None:
            raise RuntimeError("autoencoder is not fitted")
        z = self._scaled(frame)
        diff = z - self.model.predict(z)
        return np.asarray(diff**2), np.asarray(diff)

    def top(self, frame: pl.DataFrame, k: int = 3) -> tuple[np.ndarray[Any, Any], ...]:
        """Indices, directions (+1 / -1) and squared errors of the k largest deviations."""
        err, diff = self.deviations(frame)
        idx = np.argsort(-err, axis=1, kind="stable")[:, :k]
        rows = np.arange(err.shape[0])[:, None]
        direction = np.where(diff[rows, idx] >= 0, 1, -1)
        return idx, direction, err[rows, idx]

    def embedding(self, frame: pl.DataFrame) -> np.ndarray[Any, Any]:
        """Bottleneck activations (the S4 window embedding)."""
        if self.model is None:
            raise RuntimeError("autoencoder is not fitted")
        h = self._scaled(frame)
        for w, b in zip(self.model.coefs_[:2], self.model.intercepts_[:2], strict=True):
            h = np.maximum(h @ w + b, 0.0)
        return np.asarray(h)
