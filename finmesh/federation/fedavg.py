"""FedAvg in process (amendment A17: replaces Flower's simulation engine).

Every round, each client starts from the global weights, takes its local
steps (plain or DP-SGD) and returns its weights; the server averages them
with **equal weights** (client sizes are not used, so they are not
disclosed). Every client participates in every round (eight members, no
dropout to simulate); a round's minimum participation is therefore met by
construction and recorded. Only weights cross the client boundary.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from finmesh.federation.accountant import Accountant
from finmesh.federation.dpsgd import (
    BATCH,
    LEARNING_RATE,
    Adam,
    ClientData,
    UnitIndex,
    local_training,
)
from finmesh.models.neural import Encoder

ROUNDS = 50
LOCAL_STEPS = 20


def fedavg(
    clients: dict[int, ClientData],
    enc: Encoder,
    init: list[np.ndarray],
    seed: int,
    rounds: int = ROUNDS,
    local_steps: int = LOCAL_STEPS,
    dp: dict[int, dict[str, Any]] | None = None,
    on_round: Callable[[int], None] | None = None,
    lr: float = LEARNING_RATE,
    batch: int = BATCH,
) -> tuple[list[np.ndarray], dict[str, Any]]:
    """Global weights after ``rounds``; ``dp`` maps client -> {rate, noise, accountant, clip}."""
    params = [w.copy() for w in init]
    rngs = {c: np.random.default_rng([seed, c]) for c in clients}
    opts = {c: Adam(lr=lr) for c in clients}  # client optimiser state stays on the client
    index = {c: UnitIndex(d.unit) for c, d in clients.items()} if dp else {}
    clipped: dict[int, float] = {c: 0.0 for c in clients}
    for r in range(rounds):
        updates = []
        for c, data in clients.items():
            cfg = None
            if dp is not None:
                cfg = {**dp[c], "index": index[c]}
            w, stats = local_training(
                params, data, enc, local_steps, rngs[c], opts[c], cfg, batch=batch
            )
            clipped[c] += stats["clipped_share"] / rounds
            updates.append(w)
            if dp is not None:
                acc: Accountant = dp[c]["accountant"]
                acc.save()  # persisted every round: a restart resumes, never resets
        params = [np.mean([u[i] for u in updates], axis=0) for i in range(len(params))]
        if on_round:
            on_round(r)
    return params, {
        "rounds": rounds,
        "local_steps": local_steps,
        "participation": [len(clients)] * rounds,
        "clipped_share": clipped,
    }


__all__ = ["LOCAL_STEPS", "ROUNDS", "fedavg"]
