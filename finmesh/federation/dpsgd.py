"""Client training: plain SGD-with-Adam or DP-SGD at a stated privacy unit (A17).

A client holds encoded rows ``x``, targets ``y``, loss weights ``w`` and a
privacy-unit id per row (``unit``): each account-window is its own unit
under the **window unit**; under the **account unit** (week 11) the rows of
one account (at most ``k`` windows) share an id.

**DP step.** Units are Poisson-sampled with rate ``q``; each sampled unit's
full gradient is clipped to norm ``C`` (exactly, see
``finmesh.models.neural.unit_norms``); the clipped sum gets Gaussian noise
of standard deviation ``σC`` per coordinate and is divided by the
*expected* number of sampled units ``qN`` (fixed denominator, as the
accounting assumes). Adam then updates the weights; it only post-processes
the private gradient.

**Non-private step.** A uniform batch of rows, the plain mean gradient,
the same Adam: the reference against which DP is measured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from finmesh.federation.accountant import Accountant
from finmesh.models.neural import Encoder, forward_backward, summed_grads, unit_norms

CLIP = 1.0
LEARNING_RATE = 1e-3
BATCH = 512  # expected units per step (DP) or rows per step (non-private)


@dataclass
class ClientData:
    """Raw feature rows, targets, loss weights and privacy-unit ids of one client."""

    x: np.ndarray  # raw features (NaN = missing); encoded per batch
    y: np.ndarray
    w: np.ndarray
    unit: np.ndarray  # 0..U-1

    @property
    def units(self) -> int:
        return int(np.max(self.unit)) + 1 if len(self.unit) else 0


@dataclass
class Adam:
    lr: float = LEARNING_RATE
    beta1: float = 0.9
    beta2: float = 0.999
    eps: float = 1e-8
    t: int = 0
    m: list[np.ndarray] = field(default_factory=list)
    v: list[np.ndarray] = field(default_factory=list)

    def update(self, params: list[np.ndarray], grads: list[np.ndarray]) -> None:
        if not self.m:
            self.m = [np.zeros_like(p) for p in params]
            self.v = [np.zeros_like(p) for p in params]
        self.t += 1
        for p, g, m, v in zip(params, grads, self.m, self.v, strict=True):
            m *= self.beta1
            m += (1 - self.beta1) * g
            v *= self.beta2
            v += (1 - self.beta2) * g * g
            mh = m / (1 - self.beta1**self.t)
            vh = v / (1 - self.beta2**self.t)
            p -= self.lr * mh / (np.sqrt(vh) + self.eps)


class UnitIndex:
    """Rows grouped by unit, for Poisson sampling of units."""

    def __init__(self, unit: np.ndarray) -> None:
        self.order = np.argsort(unit, kind="stable")
        counts = np.bincount(unit)
        self.starts = np.concatenate([[0], np.cumsum(counts)])
        self.n = len(counts)

    def rows(self, units: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Rows of the given units and a compact unit id (0..len(units)-1) per row."""
        lens = self.starts[units + 1] - self.starts[units]
        idx = (
            np.concatenate([self.order[self.starts[u] : self.starts[u + 1]] for u in units])
            if len(units)
            else np.zeros(0, dtype=np.int64)
        )
        return idx, np.repeat(np.arange(len(units)), lens)


def dp_step(
    params: list[np.ndarray],
    opt: Adam,
    data: ClientData,
    index: UnitIndex,
    enc: Encoder,
    rate: float,
    noise: float,
    rng: np.random.Generator,
    accountant: Accountant,
    clip: float = CLIP,
) -> dict[str, float]:
    accountant.step()  # the guard first: no budget, no step
    sampled = np.nonzero(rng.random(index.n) < rate)[0]
    expected = rate * index.n
    if len(sampled):
        rows, local = index.rows(sampled)
        _, acts, grads = forward_backward(params, enc(data.x[rows]), data.y[rows], data.w[rows])
        norms = unit_norms(acts, grads, local)
        factor = np.minimum(1.0, clip / np.maximum(norms, 1e-12))
        total = summed_grads(acts, grads, factor[local])
    else:
        total = [np.zeros_like(p) for p in params]
        norms = np.zeros(0)
    noisy = [(g + rng.normal(0.0, noise * clip, g.shape)) / expected for g in total]
    opt.update(params, noisy)
    return {
        "sampled": float(len(sampled)),
        "clipped_share": float((norms > clip).mean()) if len(norms) else 0.0,
    }


def plain_step(
    params: list[np.ndarray],
    opt: Adam,
    data: ClientData,
    enc: Encoder,
    batch: int,
    rng: np.random.Generator,
) -> float:
    rows = rng.integers(0, len(data.y), batch)
    loss, acts, grads = forward_backward(params, enc(data.x[rows]), data.y[rows], data.w[rows])
    opt.update(params, [g / batch for g in summed_grads(acts, grads)])
    return loss


def local_training(
    params: list[np.ndarray],
    data: ClientData,
    enc: Encoder,
    steps: int,
    rng: np.random.Generator,
    opt: Adam | None = None,
    dp: dict[str, Any] | None = None,
    batch: int = BATCH,
) -> tuple[list[np.ndarray], dict[str, float]]:
    """``steps`` local steps from ``params`` (copied); ``dp`` = {rate, noise, accountant, index}."""
    p = [w.copy() for w in params]
    opt = opt if opt is not None else Adam()
    stats: dict[str, float] = {"clipped_share": 0.0}
    for _ in range(steps):
        if dp is None:
            plain_step(p, opt, data, enc, batch, rng)
        else:
            s = dp_step(
                p, opt, data, dp["index"], enc, dp["rate"], dp["noise"], rng, dp["accountant"]
            )
            stats["clipped_share"] += s["clipped_share"] / steps
    return p, stats


__all__ = [
    "BATCH",
    "CLIP",
    "LEARNING_RATE",
    "Adam",
    "ClientData",
    "UnitIndex",
    "dp_step",
    "local_training",
    "plain_step",
]
