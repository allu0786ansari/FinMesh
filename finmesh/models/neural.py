"""Neural scorer for the federated DP track (weeks 10-12; amendment A17).

**Encoding.** Every feature is mapped by a *piecewise-linear encoding*
(Gorishniy et al., 2022) over **fixed, data-independent** bin boundaries
chosen from the feature's kind in the schema (counts, amounts, shares,
hours, rates, log-differences), plus a missing indicator. No statistic of
any bank's data enters the encoding, so normalisation costs no privacy
budget (criterion CC4).

**Network.** Encoding → dense (64) → ReLU → dense (32) → ReLU → dense (1),
no batch normalisation, so per-example gradients are well defined for
DP-SGD. Loss: weighted binary cross-entropy on the logit.

**Per-unit gradients.** For a dense layer with input ``a`` (bias appended)
and output gradient ``d``, an example's weight gradient is the outer product
``a dᵀ``. A privacy unit's gradient (one account-window, or one account's
bag of windows) is the sum over its rows, and its squared Frobenius norm is
``Σ_ij (a_i·a_j)(d_i·d_j)`` over pairs of its rows: computed exactly from
k×k Gram matrices without materialising per-unit gradients. The clipped
sum is then ``Aᵀ (D * c)`` with each row scaled by its unit's factor ``c``.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

import numpy as np

HIDDEN: tuple[int, ...] = (64, 32)

# Fixed bin boundaries by feature kind: (transform, boundaries). Values are
# clipped to the outer boundaries after the transform.
COUNT = ("identity", (0.0, 0.5, 1.5, 2.5, 4.5, 8.5, 16.5, 32.5, 64.5, 256.0))
AMOUNT = ("log10p", (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0))
SIGNED_AMOUNT = ("slog10p", (-9.0, -6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 9.0))
SHARE = ("identity", (0.0, 0.05, 0.2, 0.4, 0.6, 0.8, 0.95, 1.0))
HOURS = ("identity", (0.0, 0.5, 1.0, 3.0, 6.0, 12.0, 24.0, 48.0, 168.0))
RATE = ("identity", (0.0, 0.1, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 128.0))
LOGDIFF = ("identity", (-8.0, -4.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 4.0, 8.0))

KIND_BY_NAME: dict[str, tuple[str, tuple[float, ...]]] = {
    "amt_out": AMOUNT,
    "amt_in": AMOUNT,
    "amt_out_max": AMOUNT,
    "amt_in_max": AMOUNT,
    "amt_net": SIGNED_AMOUNT,
    "active_span_h": HOURS,
    "in_out_delay_min_h": HOURS,
    "in_out_delay_med_h": HOURS,
    "prior_leg_rate": RATE,
    "legs_vs_history": LOGDIFF,
    "amt_vs_history": LOGDIFF,
}


def kind_of(name: str) -> tuple[str, tuple[float, ...]]:
    """The fixed encoding of a feature, from its name (shares and HHIs lie in [0, 1])."""
    if name in KIND_BY_NAME:
        return KIND_BY_NAME[name]
    if name.endswith("_share") or name.endswith("_hhi") or name == "pass_through":
        return SHARE
    return COUNT


@dataclass(frozen=True)
class Encoder:
    """Piecewise-linear encoding with a missing indicator, per feature."""

    columns: tuple[str, ...]

    @property
    def width(self) -> int:
        return sum(len(kind_of(c)[1]) - 1 + 1 for c in self.columns)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        """``x``: rows × columns (float, NaN = missing) → rows × width, float32."""
        n = x.shape[0]
        out = np.zeros((n, self.width), dtype=np.float32)
        col = 0
        for j, name in enumerate(self.columns):
            transform, bounds = kind_of(name)
            v = x[:, j].astype(np.float64)
            missing = np.isnan(v)
            v = np.where(missing, 0.0, v)
            if transform == "log10p":
                v = np.log10(1.0 + np.maximum(v, 0.0))
            elif transform == "slog10p":
                v = np.sign(v) * np.log10(1.0 + np.abs(v))
            b = np.asarray(bounds)
            v = np.clip(v, b[0], b[-1])
            lo, hi = b[:-1], b[1:]
            enc = np.clip((v[:, None] - lo) / (hi - lo), 0.0, 1.0)
            enc[missing] = 0.0
            k = len(lo)
            out[:, col : col + k] = enc
            out[:, col + k] = missing
            col += k + 1
        return out


def init_params(width: int, seed: int, hidden: tuple[int, ...] = HIDDEN) -> list[np.ndarray]:
    """He-initialised weights with the bias as the last row of each matrix."""
    rng = np.random.default_rng(seed)
    sizes = [width, *hidden, 1]
    params = []
    for d_in, d_out in itertools.pairwise(sizes):
        w = rng.normal(0.0, np.sqrt(2.0 / d_in), (d_in + 1, d_out))
        w[-1] = 0.0
        params.append(w.astype(np.float64))
    return params


def _aug(a: np.ndarray) -> np.ndarray:
    return np.concatenate([a, np.ones((a.shape[0], 1))], axis=1)


def logits(params: list[np.ndarray], x: np.ndarray) -> np.ndarray:
    h = x.astype(np.float64)
    for i, w in enumerate(params):
        h = _aug(h) @ w
        if i < len(params) - 1:
            h = np.maximum(h, 0.0)
    return np.asarray(h[:, 0])


def scores(params: list[np.ndarray], x: np.ndarray) -> np.ndarray:
    return np.asarray(1.0 / (1.0 + np.exp(-np.clip(logits(params, x), -40, 40))))


def forward_backward(
    params: list[np.ndarray], x: np.ndarray, y: np.ndarray, w: np.ndarray
) -> tuple[float, list[np.ndarray], list[np.ndarray]]:
    """Weighted BCE; returns (loss, per-layer inputs A with bias, per-layer output grads D).

    The gradient of a row's weighted loss with respect to layer ``l`` is the
    outer product ``A[l][i] ⊗ D[l][i]``.
    """
    acts = [_aug(x.astype(np.float64))]
    pre = []
    h = acts[0]
    for i, wt in enumerate(params):
        z = h @ wt
        pre.append(z)
        if i < len(params) - 1:
            h = _aug(np.maximum(z, 0.0))
            acts.append(h)
    z = np.clip(pre[-1][:, 0], -40, 40)
    p = 1.0 / (1.0 + np.exp(-z))
    loss = float(np.mean(w * (np.logaddexp(0.0, z) - y * z)))
    d = (w * (p - y))[:, None]
    grads: list[np.ndarray] = [d]
    for i in range(len(params) - 1, 0, -1):
        d = (d @ params[i][:-1].T) * (pre[i - 1] > 0)
        grads.append(d)
    return loss, acts, grads[::-1]


def unit_norms(acts: list[np.ndarray], grads: list[np.ndarray], unit: np.ndarray) -> np.ndarray:
    """Exact L2 norm of each unit's full gradient (all layers), unit ids 0..U-1 per row."""
    n_units = int(np.max(unit)) + 1 if len(unit) else 0
    sq = np.zeros(n_units)
    counts = np.bincount(unit, minlength=n_units)
    if n_units and int(np.max(counts)) == 1:  # window unit: one row per unit
        order = np.argsort(unit)
        for a, d in zip(acts, grads, strict=True):
            sq += ((a * a).sum(1) * (d * d).sum(1))[order]
        return np.sqrt(sq)
    order = np.argsort(unit, kind="stable")
    k = int(np.max(counts)) if n_units else 0
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    pos = np.arange(len(unit)) - np.repeat(starts, counts)
    rows_sorted = unit[order]
    for a, d in zip(acts, grads, strict=True):
        ap = np.zeros((n_units, k, a.shape[1]))
        dp = np.zeros((n_units, k, d.shape[1]))
        ap[rows_sorted, pos] = a[order]
        dp[rows_sorted, pos] = d[order]
        ga = np.einsum("ukd,uld->ukl", ap, ap)
        gd = np.einsum("ukh,ulh->ukl", dp, dp)
        sq += (ga * gd).sum(axis=(1, 2))
    return np.sqrt(sq)


def summed_grads(
    acts: list[np.ndarray], grads: list[np.ndarray], scale: np.ndarray | None = None
) -> list[np.ndarray]:
    """Σ_rows scale_row · A_row ⊗ D_row per layer.

    With ``scale`` = each row's clip factor, this is the clipped sum.
    """
    out = []
    for a, d in zip(acts, grads, strict=True):
        dd = d if scale is None else d * scale[:, None]
        out.append(a.T @ dd)
    return out


def flat_norm(gs: list[np.ndarray]) -> float:
    return float(np.sqrt(sum(float((g * g).sum()) for g in gs)))


__all__: list[Any] = [
    "HIDDEN",
    "Encoder",
    "forward_backward",
    "init_params",
    "kind_of",
    "logits",
    "scores",
    "summed_grads",
    "unit_norms",
]
