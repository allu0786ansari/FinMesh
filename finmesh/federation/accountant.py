"""Privacy accounting for DP-SGD clients (amendment A17; criterion CC4).

The noise multiplier is calibrated **once**, for the planned total number of
steps, with an RDP accountant (Google's ``dp_accounting``) for the
Poisson-subsampled Gaussian mechanism. Each client's accountant state is
written to disk after every round and read back on restart, so it is never
reset; a **budget guard** refuses any step beyond the plan, so the spent
ε can never exceed the target.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import dp_accounting as dpa
from dp_accounting.rdp import RdpAccountant


class BudgetExceeded(RuntimeError):
    """A client tried to take a DP step beyond its planned, calibrated budget."""


def epsilon_for(noise: float, rate: float, steps: int, delta: float) -> float:
    if steps == 0:
        return 0.0
    event = dpa.SelfComposedDpEvent(
        dpa.PoissonSampledDpEvent(rate, dpa.GaussianDpEvent(noise)), steps
    )
    acc = RdpAccountant()
    acc.compose(event)
    return float(acc.get_epsilon(delta))


def calibrate_noise(
    target_epsilon: float, rate: float, steps: int, delta: float, tol: float = 1e-3
) -> float:
    """Smallest noise multiplier whose ε after ``steps`` is at most the target."""
    lo, hi = 0.3, 1.0
    while epsilon_for(hi, rate, steps, delta) > target_epsilon:
        hi *= 2.0
        if hi > 1e4:
            raise ValueError("target ε unreachable")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if epsilon_for(mid, rate, steps, delta) > target_epsilon:
            lo = mid
        else:
            hi = mid
    return hi


@dataclass
class AccountantState:
    client: int
    target_epsilon: float
    delta: float
    rate: float
    noise: float
    steps_planned: int
    steps_done: int = 0

    @property
    def spent(self) -> float:
        return epsilon_for(self.noise, self.rate, self.steps_done, self.delta)


class Accountant:
    """One client's persistent accountant with a budget guard."""

    def __init__(self, path: Path, state: AccountantState) -> None:
        self.path = path
        if path.exists():  # never reset: resume what is on disk
            saved = AccountantState(**json.loads(path.read_text()))
            same = (saved.client, saved.target_epsilon, saved.rate, saved.steps_planned) == (
                state.client,
                state.target_epsilon,
                state.rate,
                state.steps_planned,
            )
            if not same:
                raise ValueError(f"{path} holds a different plan; refusing to reuse it")
            state = saved
        self.state = state
        self.save()

    @classmethod
    def plan(
        cls,
        path: Path,
        client: int,
        target_epsilon: float,
        delta: float,
        rate: float,
        steps: int,
    ) -> Accountant:
        if path.exists():
            saved = AccountantState(**json.loads(path.read_text()))
            return cls(path, saved)
        noise = calibrate_noise(target_epsilon, rate, steps, delta)
        return cls(path, AccountantState(client, target_epsilon, delta, rate, noise, steps))

    def step(self, n: int = 1) -> None:
        if self.state.steps_done + n > self.state.steps_planned:
            raise BudgetExceeded(
                f"client {self.state.client}: {self.state.steps_done + n} steps planned for "
                f"{self.state.steps_planned} (ε {self.state.target_epsilon})"
            )
        self.state.steps_done += n

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(self.state)))

    def report(self) -> dict[str, float]:
        return {**asdict(self.state), "epsilon_spent": self.state.spent}


__all__ = ["Accountant", "AccountantState", "BudgetExceeded", "calibrate_noise", "epsilon_for"]
