"""Applying a fitted isotonic calibration (fitting needs labels: finmesh.training).

A calibrator is a monotone step function stored as two arrays (score knots
and probabilities), so it serialises to JSON and is shared with nothing but
the bank that fitted it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Isotonic:
    knots: tuple[float, ...]
    values: tuple[float, ...]

    def __call__(self, scores: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.asarray(np.interp(scores, np.asarray(self.knots), np.asarray(self.values)))

    def to_dict(self) -> dict[str, list[float]]:
        return {"knots": list(self.knots), "values": list(self.values)}
