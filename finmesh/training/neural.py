"""Shared pieces of the neural track (weeks 10-12; amendments A17, A18).

* :func:`client_data`: one client's rows at the **window unit** (each
  account-window is a unit) or the **account unit** (one account's bag of at
  most :data:`BAG_CAP` windows, chosen by a fixed hash; the rest are dropped).
* :class:`DpHparams` and :func:`dp_hparams`: the clip norm, expected batch and
  learning rate used by every DP run on a dataset, frozen in
  ``finmesh/schemas/dp_hparams.json`` by ``finmesh dp-tune`` on the proxy
  federation of the same regime (HI-Small for HI-Medium, LI-Small for
  LI-Medium; A18). Without an entry, the A17 values apply.
* :func:`train_private`: FedAvg with DP-SGD at a target ε, one accountant per
  client in the run directory; returns the weights and the accounting report.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from finmesh.federation.accountant import Accountant
from finmesh.federation.dpsgd import BATCH, CLIP, LEARNING_RATE, ClientData
from finmesh.federation.fedavg import LOCAL_STEPS, ROUNDS, fedavg
from finmesh.models.neural import Encoder
from finmesh.training.data import Rows

POS_WEIGHT = 10.0
DELTA_FACTOR = 0.1  # δ = DELTA_FACTOR / N units
BAG_CAP = 8  # windows per account under the account unit
HPARAMS_PATH = Path(__file__).resolve().parent.parent / "schemas" / "dp_hparams.json"
UNITS: tuple[str, ...] = ("window", "account")


@dataclass(frozen=True)
class DpHparams:
    clip: float = CLIP
    batch: int = BATCH
    lr: float = LEARNING_RATE
    source: str = "A17 defaults"
    local_steps: int = LOCAL_STEPS  # per round; a fixed example budget (A18)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def regime(dataset: str) -> str:
    """HI or LI: the proxy federation used to tune a dataset's DP settings."""
    return dataset.split("-")[0].upper()


def dp_hparams(dataset: str) -> DpHparams:
    if not HPARAMS_PATH.exists():
        return DpHparams()
    doc = json.loads(HPARAMS_PATH.read_text())
    entry = doc.get("regimes", {}).get(regime(dataset))
    if not entry:
        return DpHparams()
    return DpHparams(
        float(entry["clip"]),
        int(entry["batch"]),
        float(entry["lr"]),
        entry.get("source", ""),
        int(entry.get("local_steps", steps_for(int(entry["batch"])))),
    )


def steps_for(batch: int) -> int:
    """Local steps per round that keep every batch at the same example budget (A18)."""
    return max(1, round(LOCAL_STEPS * BATCH / batch))


def write_dp_hparams(dataset: str, hp: DpHparams, evidence: dict[str, Any]) -> Path:
    doc = json.loads(HPARAMS_PATH.read_text()) if HPARAMS_PATH.exists() else {"regimes": {}}
    doc.setdefault("name", "finmesh-dp-hparams")
    doc.setdefault(
        "rule",
        "A18: DP-SGD clip norm, expected batch and learning rate chosen on the proxy "
        "federation of the same regime (HI-Small, LI-Small), never on the Medium sets.",
    )
    doc["regimes"][regime(dataset)] = {**hp.to_dict(), "evidence": evidence}
    HPARAMS_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    return HPARAMS_PATH


def _bag_keep(account: np.ndarray, window: np.ndarray, cap: int) -> np.ndarray:
    """Keep at most ``cap`` rows per account, chosen by a fixed hash of (account, window)."""
    frame = pl.DataFrame({"a": account, "w": window}).with_row_index("i")
    ranked = frame.with_columns(
        pl.struct("a", "w").hash(seed=4242).rank("ordinal").over("a").alias("r")
    )
    return np.asarray(ranked["r"].to_numpy() <= cap)


def client_data(fit: Rows, member: int | None, unit: str = "window") -> ClientData:
    """A client's training rows at a privacy unit (``member`` None = every member)."""
    if unit not in UNITS:
        raise ValueError(unit)
    sel = np.ones(len(fit.y), dtype=bool) if member is None else fit.member == member
    if unit == "account":
        assert fit.account is not None and fit.window is not None
        keep = np.zeros(len(sel), dtype=bool)
        idx = np.nonzero(sel)[0]
        keep[idx] = _bag_keep(fit.account[idx], fit.window[idx], BAG_CAP)
        sel = keep
    y = fit.y[sel].astype(np.float64)
    if unit == "window":
        units = np.arange(int(sel.sum()))
    else:
        assert fit.account is not None
        _, units = np.unique(fit.account[sel], return_inverse=True)
    return ClientData(x=fit.x[sel], y=y, w=np.where(y == 1, POS_WEIGHT, 1.0), unit=units)


def train_private(
    clients: dict[int, ClientData],
    enc: Encoder,
    init: list[np.ndarray],
    seed: int,
    epsilon: float,
    hp: DpHparams,
    run_dir: Path,
    rounds: int = ROUNDS,
    local_steps: int | None = None,
    unit: str = "window",
) -> tuple[list[np.ndarray], dict[str, Any]]:
    """``local_steps`` None = the setting's own (fixed example budget)."""
    local_steps = hp.local_steps if local_steps is None else local_steps
    steps = rounds * local_steps
    dp: dict[int, dict[str, Any]] = {}
    for m, d in clients.items():
        n = d.units
        rate = min(1.0, hp.batch / n)
        acc = Accountant.plan(
            run_dir / f"client{m}.json",
            client=m,
            target_epsilon=epsilon,
            delta=DELTA_FACTOR / n,
            rate=rate,
            steps=steps,
        )
        dp[m] = {"rate": rate, "noise": acc.state.noise, "accountant": acc, "clip": hp.clip}
    params, info = fedavg(clients, enc, init, seed, rounds, local_steps, dp, lr=hp.lr)
    report = {
        "unit": unit,
        "hparams": hp.to_dict(),
        "clients": {str(m): dp[m]["accountant"].report() for m in dp},
        "units": {str(m): int(d.units) for m, d in clients.items()},
        "clipped_share": {str(k): v for k, v in info["clipped_share"].items()},
    }
    return params, report


__all__ = [
    "BAG_CAP",
    "DELTA_FACTOR",
    "POS_WEIGHT",
    "UNITS",
    "DpHparams",
    "client_data",
    "dp_hparams",
    "regime",
    "steps_for",
    "train_private",
    "write_dp_hparams",
]
