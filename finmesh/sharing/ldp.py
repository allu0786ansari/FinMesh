"""S3: the minimised record released through local differential privacy.

Each bucketed field of the S2 record goes through **k-ary randomised
response** (k-RR): with probability e^ε_f / (e^ε_f + k - 1) the true value
is reported, otherwise one of the other k - 1 values uniformly. A record has
:data:`LDP_FIELDS` fields; the total ε is split evenly across them
(ε_f = ε / n), so by sequential composition each released record is
ε-LDP. The time bucket and the alert flag are not noised: they are exactly
what S1 already discloses, so S3 leaks at most S1 plus an ε-LDP record.

**Memoisation.** A responder releases each of its records at most once per
epoch; a second request for the same record gets the same noisy values,
which costs no further privacy (as in RAPPOR's permanent response). Fresh
noise on every request would let a peer average it away.

**Per-account budget.** Distinct records released about one account within
an epoch compose: the node keeps a ledger of ε spent per (account, epoch)
and, once the next release would exceed :data:`EPSILON_CAP` (default 8), it
answers with the alert flag only (S1 content). The ledger is part of the
privacy ledger of the prototype.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from finmesh.sharing.evidence import WIRE_FIELDS, load_evidence_schema

EPSILONS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0, 8.0)
EPSILON_CAP = 8.0  # per account and epoch, summed over distinct released records
CLEAR_FIELDS = ("window", "alert")  # S1 content, released in the clear
LDP_FIELDS: tuple[str, ...] = tuple(f for f in WIRE_FIELDS if f not in CLEAR_FIELDS)


def field_domains(n_features: int) -> dict[str, tuple[int, ...]]:
    """The values each noised field can take (randomised response draws from these)."""
    s = load_evidence_schema()
    out: dict[str, tuple[int, ...]] = {"prob_bucket": tuple(range(len(s.prob_edges) + 1))}
    for k in range(s.top):
        out[f"dev{k}_feature"] = tuple(range(n_features))
        out[f"dev{k}_direction"] = (-1, 1)
        out[f"dev{k}_magnitude"] = tuple(range(len(s.magnitude_edges) + 2))
    for name, _, edges in s.counters:
        out[f"c_{name}"] = tuple(range(len(edges) + 2))
    assert set(out) == set(LDP_FIELDS)
    return out


def keep_probability(epsilon: float, k: int) -> float:
    """P(report the true value) under k-RR at ``epsilon``."""
    return math.exp(epsilon) / (math.exp(epsilon) + k - 1)


def k_rr(
    values: np.ndarray, domain: tuple[int, ...], epsilon: float, rng: np.random.Generator
) -> np.ndarray:
    """k-ary randomised response, vectorised over ``values`` (all in ``domain``)."""
    dom = np.asarray(domain)
    k = len(dom)
    pos = np.searchsorted(dom, values)
    if np.any((pos >= k) | (dom[np.minimum(pos, k - 1)] != values)):
        raise ValueError("value outside the field's domain")
    keep = rng.random(len(values)) < keep_probability(epsilon, k)
    other = rng.integers(0, k - 1, len(values))
    other = other + (other >= pos)  # uniform over the k - 1 other values
    return np.where(keep, dom[pos], dom[np.minimum(other, k - 1)])


@dataclass
class LdpReleaser:
    """One responder's S3 mechanism: memoised releases and the per-account ledger."""

    epsilon: float
    n_features: int
    seed: int
    cap: float = EPSILON_CAP
    released: dict[int, tuple[int, ...]] = field(default_factory=dict)  # record row -> values
    ledger: dict[tuple[int, int], float] = field(default_factory=lambda: defaultdict(float))
    withheld: int = 0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._domains = field_domains(self.n_features)
        self._idx = [WIRE_FIELDS.index(f) for f in LDP_FIELDS]
        self.per_field = self.epsilon / len(LDP_FIELDS)

    def release(
        self, row: int, account: int, epoch: int, wire: tuple[int, ...]
    ) -> tuple[int, ...] | None:
        """Noisy S2 values for record ``row`` (WIRE_FIELDS order), or None when over budget."""
        if row in self.released:
            return self.released[row]
        key = (account, epoch)
        if self.ledger[key] + self.epsilon > self.cap + 1e-9:
            self.withheld += 1
            return None
        self.ledger[key] += self.epsilon
        out = list(wire)
        for i, name in zip(self._idx, LDP_FIELDS, strict=True):
            out[i] = int(
                k_rr(np.array([wire[i]]), self._domains[name], self.per_field, self._rng)[0]
            )
        values = tuple(out)
        self.released[row] = values
        return values

    @property
    def max_account_epsilon(self) -> float:
        return max(self.ledger.values(), default=0.0)


__all__ = [
    "CLEAR_FIELDS",
    "EPSILONS",
    "EPSILON_CAP",
    "LDP_FIELDS",
    "LdpReleaser",
    "field_domains",
    "k_rr",
    "keep_probability",
]
