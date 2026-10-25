"""Uncertainty for scheme- and window-level metrics (proposal Section 9).

* Scheme-level rates: a cluster bootstrap over schemes. With several seeds,
  each scheme's outcome is first averaged across seeds, then schemes are
  resampled, so the interval reflects scheme sampling, not just seed noise.
* Window-level metrics (AUPRC, AUROC): a cluster bootstrap over accounts,
  using Poisson(1) weights per account, so all windows of one account move
  together (``finmesh.eval.metrics.RankedScores.bootstrap``).
* Comparisons: a paired bootstrap over the same schemes, a two-sided p-value
  from the share of replicates on the other side of zero, and Holm's
  step-down correction across a family of comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

DEFAULT_REPS = 1000


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float
    reps: int

    def to_dict(self) -> dict[str, float | int]:
        return {"estimate": self.estimate, "low": self.low, "high": self.high, "reps": self.reps}


def _percentiles(values: NDArray[np.float64], estimate: float, reps: int) -> Interval:
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return Interval(estimate, float("nan"), float("nan"), reps)
    low, high = np.percentile(values, [2.5, 97.5])
    return Interval(estimate, float(low), float(high), reps)


def scheme_rate_ci(
    outcomes: NDArray[np.generic], reps: int = DEFAULT_REPS, seed: int = 0
) -> Interval:
    """Mean of per-scheme outcomes (rows = schemes, optional columns = seeds)."""
    x = np.asarray(outcomes, dtype=np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    n = len(x)
    if n == 0:
        return Interval(float("nan"), float("nan"), float("nan"), reps)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(reps, n))
    return _percentiles(x[idx].mean(axis=1), float(x.mean()), reps)


def paired_difference(
    a: NDArray[np.generic], b: NDArray[np.generic], reps: int = DEFAULT_REPS, seed: int = 0
) -> tuple[Interval, float]:
    """Mean of ``a - b`` over the same schemes, its interval and a two-sided p-value."""
    xa = np.asarray(a, dtype=np.float64)
    xb = np.asarray(b, dtype=np.float64)
    if xa.ndim == 2:
        xa = xa.mean(axis=1)
    if xb.ndim == 2:
        xb = xb.mean(axis=1)
    if xa.shape != xb.shape:
        raise ValueError("paired outcomes must cover the same schemes")
    d = xa - xb
    n = len(d)
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, n, size=(reps, n))].mean(axis=1)
    interval = _percentiles(means, float(d.mean()), reps)
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return interval, float(min(1.0, p))


def holm(pvalues: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def interval_from(values: NDArray[np.float64], estimate: float) -> Interval:
    """Percentile interval of bootstrap replicates around a point estimate."""
    return _percentiles(np.asarray(values, dtype=np.float64), estimate, len(values))
