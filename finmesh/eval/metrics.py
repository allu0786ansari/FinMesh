"""Window-level ranking metrics with exact handling of ties and optional weights.

Weights make the same code serve the cluster bootstrap (Poisson weights per
cluster). Tied scores are treated as one threshold, as scikit-learn does, so a
detector cannot gain from the order in which ties happen to be stored.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _prepare(
    y: NDArray[np.generic], s: NDArray[np.generic], w: NDArray[np.generic] | None
) -> tuple[FloatArray, FloatArray, FloatArray]:
    yy: FloatArray = np.asarray(y, dtype=np.float64)
    ss: FloatArray = np.asarray(s, dtype=np.float64)
    if yy.shape != ss.shape:
        raise ValueError("labels and scores differ in length")
    if np.isnan(ss).any():
        raise ValueError("scores contain NaN; fill unscored windows before evaluating")
    ww: FloatArray = np.ones_like(yy) if w is None else np.asarray(w, dtype=np.float64)
    return yy, ss, ww


class RankedScores:
    """Scores sorted once; exact AUPRC and AUROC for any row weights, fast.

    Tied scores form one threshold group. Both metrics need, per group that
    contains a positive, only the weighted positives in it (dTP), the
    cumulative weight up to its end, and the cumulative weight before it.
    With about one positive in a thousand, a weighted evaluation then costs
    one gather and one cumulative sum over the rows, instead of a dozen full
    passes: what makes a 200-replicate bootstrap on 11 M account-windows cheap.

    With weights ``w`` (``P`` = weighted positives, ``N`` = weighted negatives):

    * AUPRC = sum over positive groups of dTP * TP / (TP + FP), divided by P;
    * AUROC = sum over positive groups of dTP * (negatives strictly below the
      group + half the negatives tied in it), divided by P * N.
    """

    def __init__(self, y: NDArray[np.generic], s: NDArray[np.generic]) -> None:
        yy, ss, _ = _prepare(y, s, None)
        self.n = len(yy)
        self.order = np.argsort(-ss, kind="mergesort")
        y_sorted = yy[self.order]
        s_sorted = ss[self.order]
        ends = np.r_[np.flatnonzero(np.diff(s_sorted)), self.n - 1] if self.n else np.zeros(0, int)
        starts = np.r_[0, ends[:-1] + 1] if self.n else np.zeros(0, int)
        self.pos_rows = np.flatnonzero(y_sorted > 0)  # sorted positions of positives
        self.neg_mask = y_sorted <= 0
        group_of_pos = np.searchsorted(ends, self.pos_rows)
        groups, first_idx = np.unique(group_of_pos, return_index=True)
        # Positives of one group are contiguous in pos_rows: their slice ends here.
        self.pos_group_slice_end = np.r_[first_idx[1:], len(self.pos_rows)]
        self.pos_group_end = ends[groups]
        self.pos_group_start = starts[groups]

    def _weighted(self, w_sorted: FloatArray) -> tuple[float, float]:
        if self.n == 0 or len(self.pos_rows) == 0:
            return float("nan"), float("nan")
        cum = np.cumsum(w_sorted)
        cum_pos = np.cumsum(w_sorted[self.pos_rows])
        tp = cum_pos[self.pos_group_slice_end - 1]  # cumulative positives at each group end
        d_tp = np.diff(np.r_[0.0, tp])
        total_end = cum[self.pos_group_end]
        before = np.where(self.pos_group_start > 0, cum[self.pos_group_start - 1], 0.0)
        p = tp[-1]
        n_neg = cum[-1] - p
        if p <= 0:
            return float("nan"), float("nan")
        ap = float(np.sum(d_tp * tp / np.maximum(total_end, 1e-300)) / p)
        if n_neg <= 0:
            return ap, float("nan")
        fp_end = total_end - tp
        fp_before = before - (tp - d_tp)
        tied_neg = fp_end - fp_before
        below = n_neg - fp_end
        auc = float(np.sum(d_tp * (below + 0.5 * tied_neg)) / (p * n_neg))
        return ap, auc

    def stats(self, w: NDArray[np.generic] | None = None) -> tuple[float, float]:
        """(AUPRC, AUROC) with optional row weights in the original row order."""
        w_sorted = np.ones(self.n) if w is None else np.asarray(w, dtype=np.float64)[self.order]
        return self._weighted(w_sorted)

    def average_precision(self, w: NDArray[np.generic] | None = None) -> float:
        return self.stats(w)[0]

    def roc_auc(self, w: NDArray[np.generic] | None = None) -> float:
        return self.stats(w)[1]

    def bootstrap(
        self, clusters: NDArray[np.generic], reps: int, seed: int
    ) -> tuple[FloatArray, FloatArray]:
        """AUPRC and AUROC under Poisson(1) weights drawn per cluster (account)."""
        _, inverse = np.unique(np.asarray(clusters), return_inverse=True)
        inverse_sorted = inverse[self.order]
        n_clusters = int(np.max(inverse)) + 1 if len(inverse) else 0
        rng = np.random.default_rng(seed)
        ap = np.empty(reps)
        auc = np.empty(reps)
        for r in range(reps):
            w_sorted = rng.poisson(1.0, size=n_clusters).astype(np.float64)[inverse_sorted]
            ap[r], auc[r] = self._weighted(w_sorted)
        return ap, auc


def average_precision(
    y: NDArray[np.generic], s: NDArray[np.generic], w: NDArray[np.generic] | None = None
) -> float:
    """Area under the precision-recall curve as a step function (AUPRC)."""
    return RankedScores(y, s).average_precision(w)


def roc_auc(
    y: NDArray[np.generic], s: NDArray[np.generic], w: NDArray[np.generic] | None = None
) -> float:
    return RankedScores(y, s).roc_auc(w)


def precision_at_k(y: NDArray[np.generic], s: NDArray[np.generic], k: int) -> float:
    """Precision among the ``k`` highest scores; ties at the cut are averaged."""
    yy, ss, _ = _prepare(y, s, None)
    if k <= 0 or len(yy) == 0:
        return float("nan")
    k = min(k, len(yy))
    order = np.argsort(-ss, kind="mergesort")
    cut = ss[order[k - 1]]
    above = ss > cut
    tied = ss == cut
    n_above = int(above.sum())
    take_from_ties = k - n_above
    expected_tp = yy[above].sum() + take_from_ties * yy[tied].mean()
    return float(expected_tp / k)
