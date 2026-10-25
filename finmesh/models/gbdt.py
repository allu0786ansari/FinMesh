"""LightGBM detector (proposal Section 8.2): the primary local model and the oracle.

Label-free by construction: :func:`fit` takes plain arrays prepared by
``finmesh.training``, and :func:`score` reads only feature columns. Settings
are fixed here, not tuned on validation data, so validation stays an honest
estimate for the G1 comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import lightgbm as lgb
import numpy as np
import polars as pl

PARAMS: dict[str, Any] = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "metric": "average_precision",
    "deterministic": True,
    "force_row_wise": True,
    "verbosity": -1,
}
MAX_ROUNDS = 1000
EARLY_STOPPING = 50


@dataclass
class GBDT:
    features: tuple[str, ...]
    seed: int
    booster: lgb.Booster | None = None
    info: dict[str, Any] = field(default_factory=dict)

    def fit(
        self,
        x: np.ndarray[Any, Any],
        y: np.ndarray[Any, Any],
        w: np.ndarray[Any, Any],
        x_stop: np.ndarray[Any, Any],
        y_stop: np.ndarray[Any, Any],
        w_stop: np.ndarray[Any, Any],
    ) -> GBDT:
        """Train with early stopping on a later, held-out slice of the training period."""
        params = {**PARAMS, "seed": self.seed}
        train = lgb.Dataset(x, y, weight=w, feature_name=list(self.features), free_raw_data=True)
        stop = lgb.Dataset(x_stop, y_stop, weight=w_stop, reference=train)
        self.booster = lgb.train(
            params,
            train,
            num_boost_round=MAX_ROUNDS,
            valid_sets=[stop],
            callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False)],
        )
        self.info = {
            "rounds": int(self.booster.best_iteration or self.booster.current_iteration()),
            "train_rows": len(y),
            "train_positives": int(np.sum(y)),
            "stop_rows": len(y_stop),
            "stop_auprc": float(self.booster.best_score["valid_0"]["average_precision"]),
        }
        return self

    def score(self, frame: pl.DataFrame) -> np.ndarray[Any, Any]:
        if self.booster is None:
            raise RuntimeError("model is not fitted")
        x = matrix(frame, self.features)
        return np.asarray(self.booster.predict(x, num_iteration=self.booster.best_iteration))

    def importance(self) -> dict[str, float]:
        if self.booster is None:
            return {}
        gain = self.booster.feature_importance(importance_type="gain")
        total = float(gain.sum()) or 1.0
        return {f: float(g) / total for f, g in zip(self.features, gain, strict=True)}


def matrix(frame: pl.DataFrame, features: tuple[str, ...]) -> np.ndarray[Any, Any]:
    """float32 matrix with NaN for missing values (LightGBM routes them natively)."""
    return frame.select(pl.col(list(features)).cast(pl.Float32)).to_numpy().astype(np.float32)
