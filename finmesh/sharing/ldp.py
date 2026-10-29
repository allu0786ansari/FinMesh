"""S3: the minimised record released through local differential privacy.

Each bucketed field of the S2 record goes through **k-ary randomised
response** (k-RR): with probability e^ε_f / (e^ε_f + k - 1) the true value
is reported, otherwise one of the other k - 1 values uniformly. A record has
:data:`LDP_FIELDS` fields; the total ε is split evenly across them
(ε_f = ε / n), so by sequential composition each released record is
ε-LDP. The time bucket and the alert flag are not noised: they are exactly
what S1 already discloses, so S3 leaks at most S1 plus an ε-LDP record.

**Every request gets a record (amendment A16).** Whether a record exists says
that the account's score reached the evidence floor, so a responder with no
record in range releases a **dummy** (probability bucket 0, no deviation,
counters missing) through the same mechanism, and the record's time field is
always the end of the requested range. Existence is then protected by the
same ε as the values. (Week 8 answered "no record" in the clear; the audit
showed S3's leakage did not fall with ε for that reason.)

**Memoisation.** A responder releases each of its records at most once per
epoch; a second request for the same record in the epoch gets the same noisy
values, which costs no further privacy (as in RAPPOR's permanent response).
Fresh noise on every request would let a peer average it away. A new epoch
(new token key) gets a fresh release, charged to that epoch's budget, so the
same noisy values never link an account across a key rotation (attack A4).

**Per-account budget.** Distinct records released about one account within
an epoch compose: the node keeps a ledger of ε spent per (account, epoch)
and, once the next release would exceed :data:`EPSILON_CAP` (default 8), it
answers with the alert flag only (S1 content). The ledger is part of the
privacy ledger of the prototype.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from finmesh.sharing.evidence import WIRE_FIELDS, load_evidence_schema

EPSILONS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0, 8.0)
EPSILON_CAP = 8.0  # per account and epoch, summed over distinct released records
CLEAR_FIELDS = ("window", "alert")  # S1 content, released in the clear
LDP_FIELDS: tuple[str, ...] = tuple(f for f in WIRE_FIELDS if f not in CLEAR_FIELDS)


def dummy_wire(window: int) -> tuple[int, ...]:
    """The record released when none exists: bucket 0, no deviation, counters missing."""
    s = load_evidence_schema()
    values = {"window": window, "alert": 0, "prob_bucket": 0}
    for k in range(s.top):
        values |= {f"dev{k}_feature": 0, f"dev{k}_direction": 1, f"dev{k}_magnitude": 0}
    for name, _, edges in s.counters:
        values[f"c_{name}"] = len(edges) + 1
    return tuple(int(values[f]) for f in WIRE_FIELDS)


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
    # memo key (a record row, or ("dummy", ledger key)) -> released values
    released: dict[Any, tuple[int, ...]] = field(default_factory=dict)
    # (account or token, epoch) -> epsilon spent on distinct releases
    ledger: dict[Any, float] = field(default_factory=lambda: defaultdict(float))
    withheld: int = 0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._domains = field_domains(self.n_features)
        self._idx = [WIRE_FIELDS.index(f) for f in LDP_FIELDS]
        self.per_field = self.epsilon / len(LDP_FIELDS)
        # Vectorised k-RR over the record's fields: one flat table of domain values.
        doms = [self._domains[f] for f in LDP_FIELDS]
        self._k = np.array([len(d) for d in doms])
        self._offset = np.concatenate([[0], np.cumsum(self._k)[:-1]])
        self._flat = np.concatenate([np.asarray(d) for d in doms])
        self._pos = [{v: i for i, v in enumerate(d)} for d in doms]
        self._keep = np.array([keep_probability(self.per_field, int(k)) for k in self._k])

    def release(
        self, memo: Hashable, subject: Hashable, epoch: int, wire: tuple[int, ...]
    ) -> tuple[int, ...] | None:
        """Noisy values for ``wire`` (WIRE_FIELDS order), or None when over budget.

        ``memo`` identifies the release (a record row, or a dummy for one subject):
        the same memo always returns the same values. ``subject`` is the account
        (or, when the node holds no record of it in the epoch, its token).
        """
        if memo in self.released:
            return self.released[memo]
        key = (subject, epoch)
        if self.ledger[key] + self.epsilon > self.cap + 1e-9:
            self.withheld += 1
            return None
        self.ledger[key] += self.epsilon
        try:
            pos = np.array([p[wire[i]] for p, i in zip(self._pos, self._idx, strict=True)])
        except KeyError as exc:
            raise ValueError("value outside the field's domain") from exc
        u = self._rng.random((2, len(pos)))
        other = (u[1] * (self._k - 1)).astype(np.int64)
        other = other + (other >= pos)  # uniform over the k - 1 other values
        chosen = np.where(u[0] < self._keep, pos, other)
        noisy = self._flat[self._offset + chosen]
        out = list(wire)
        for j, i in enumerate(self._idx):
            out[i] = int(noisy[j])
        values = tuple(out)
        self.released[memo] = values
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
    "dummy_wire",
    "field_domains",
    "k_rr",
    "keep_probability",
]
