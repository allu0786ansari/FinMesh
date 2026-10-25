"""Token service and token clients (proposal Section 8.4; criterion CC5).

A **token** is the OPRF output for an account identifier under the key of one
epoch: banks that see the same account (its holder, or a counterparty that
paid it) obtain the same token in that epoch, and nothing else. Tokens change
from epoch to epoch, so they cannot be linked across epochs without a query.

* :class:`TokenService` holds the per-epoch keys. It evaluates blinded points
  for a bank, meters queries per bank and epoch against a budget, and logs
  counts only (no identifiers, no tokens). It is the only holder of a key.
* :class:`TokenClient` runs at a bank. It blinds identifiers, sends the
  blinded points through a transport callable (in-process here, a network
  call in the demo path) and unblinds the answers. It never sees a key.
* :class:`HashTokenClient` is the **control** for the leakage audit (A1):
  tokens from a shared HMAC key every bank holds, the scheme the OPRF
  replaces. Any bank can tokenise candidate identifiers offline with it.

Identifiers here are the 64-bit hashes of ``<bank>:<account>`` used across
FinMesh, standing in for the account number in a payment message.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from finmesh.matching import oprf

EPOCH_WINDOWS = 28  # 7 days of 6 h windows: one key per epoch
QUERY_BUDGET = 250_000  # blinded evaluations per bank and epoch
TOKEN_BYTES = 16  # truncated PRF output; collisions are negligible at AMLworld scale

Transport = Callable[[int, int, list[bytes]], list[bytes]]


def epoch_of(window: int) -> int:
    return window // EPOCH_WINDOWS


def identifier(account: int) -> bytes:
    """Wire form of an account identifier (8 bytes, big-endian)."""
    return int(account).to_bytes(8, "big")


class BudgetExceeded(PermissionError):
    """A bank asked for more evaluations than its budget for the epoch allows."""


@dataclass
class LogEntry:
    time: str
    bank: int
    epoch: int
    evaluated: int
    refused: int


class TokenService:
    """Holds one OPRF key per epoch, derived from a seed only the service knows."""

    def __init__(self, seed: bytes | None = None, budget: int = QUERY_BUDGET) -> None:
        self.__seed = seed if seed is not None else secrets.token_bytes(32)
        self.__keys: dict[int, oprf.KeyPair] = {}
        self.budget = budget
        self.used: dict[tuple[int, int], int] = defaultdict(int)
        self.log: list[LogEntry] = []

    def __repr__(self) -> str:
        return f"TokenService(epochs={sorted(self.__keys)}, budget={self.budget})"

    def __getstate__(self) -> Any:
        raise TypeError("the token service cannot be serialised: it holds the keys")

    def _key(self, epoch: int) -> oprf.KeyPair:
        if epoch not in self.__keys:
            self.__keys[epoch] = oprf.derive_key_pair(self.__seed, b"finmesh epoch %d" % epoch)
        return self.__keys[epoch]

    def evaluate(self, bank: int, epoch: int, blinded: list[bytes]) -> list[bytes]:
        """Blind evaluation for ``bank`` in ``epoch``; refuses the batch if over budget."""
        key = (bank, epoch)
        if self.used[key] + len(blinded) > self.budget:
            self.log.append(self._entry(bank, epoch, 0, len(blinded)))
            raise BudgetExceeded(
                f"bank {bank} would exceed {self.budget} evaluations in epoch {epoch}"
            )
        out = [oprf.blind_evaluate(self._key(epoch).secret, b) for b in blinded]
        self.used[key] += len(blinded)
        self.log.append(self._entry(bank, epoch, len(blinded), 0))
        return out

    def _entry(self, bank: int, epoch: int, evaluated: int, refused: int) -> LogEntry:
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        return LogEntry(stamp, bank, epoch, evaluated, refused)

    def audit_evaluate(self, epoch: int, ident: bytes) -> bytes:
        """Direct evaluation for the leakage audit's ground truth only (never a bank)."""
        return oprf.evaluate(self._key(epoch).secret, ident)[:TOKEN_BYTES]


@dataclass
class TokenClient:
    """Bank side: blind, query through ``transport``, unblind. Caches per epoch."""

    bank: int
    transport: Transport
    cache: dict[tuple[int, bytes], bytes] = field(default_factory=dict)
    queries: int = 0

    def tokens(self, epoch: int, idents: Sequence[bytes]) -> list[bytes]:
        missing = list(dict.fromkeys(i for i in idents if (epoch, i) not in self.cache))
        if missing:
            blinds = [oprf.blind(i) for i in missing]
            evaluated = self.transport(self.bank, epoch, [b for _, b in blinds])
            self.queries += len(missing)
            for ident, (r, _), ev in zip(missing, blinds, evaluated, strict=True):
                self.cache[(epoch, ident)] = oprf.finalize(ident, r, ev)[:TOKEN_BYTES]
        return [self.cache[(epoch, i)] for i in idents]


@dataclass
class HashTokenClient:
    """Shared-key hashing control (A1 only): every bank holds ``shared_key``."""

    shared_key: bytes
    bank: int = -1
    queries: int = 0

    def tokens(self, epoch: int, idents: Iterable[bytes]) -> list[bytes]:
        key = hashlib.sha256(self.shared_key + b"epoch %d" % epoch).digest()
        return [hmac.new(key, i, hashlib.sha256).digest()[:TOKEN_BYTES] for i in idents]
