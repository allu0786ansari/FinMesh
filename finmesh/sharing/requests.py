"""Evidence requests: signed, expiring, one-time, purpose-bound, rate-limited.

* The **issuer** (the orchestration component) signs each request with an
  Ed25519 key; nodes hold only the public key, so a node can check a request
  but never forge one (threat ADV-5 is bounded by what the issuer signs).
* The **guard** at each responder refuses a request whose signature fails,
  that has expired, whose nonce was seen before (one-time), whose hop limit
  is spent, whose purpose is undeclared, or whose token has already had
  :data:`RATE_PER_TOKEN` answers in the epoch (limits probing of one account).
* Received evidence is kept for :data:`RETENTION_WINDOWS` and then dropped.
"""

from __future__ import annotations

import secrets
from collections import defaultdict
from dataclasses import dataclass, field, replace

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from finmesh.sharing.messages import PURPOSES, EvidenceRequest, EvidenceResponse

RATE_PER_TOKEN = 20  # answers per token and epoch, per responder
RETENTION_WINDOWS = 12  # 72 h
EXPIRY_WINDOWS = 1  # a request must be answered within the next window
HOP_LIMIT = 1  # responders never forward


class RequestIssuer:
    """Signs requests on behalf of nodes; holds the only signing key."""

    def __init__(self) -> None:
        self.__key = Ed25519PrivateKey.generate()
        self.public_key: Ed25519PublicKey = self.__key.public_key()
        self._next = 0

    def issue(
        self,
        requester: int,
        responder: int,
        token: bytes,
        epoch: int,
        window_lo: int,
        window_hi: int,
        requester_bucket: int,
        now: int,
        purpose: str = "alert_triage",
    ) -> EvidenceRequest:
        self._next += 1
        request = EvidenceRequest(
            request_id=self._next,
            requester=requester,
            responder=responder,
            token=token,
            epoch=epoch,
            window_lo=window_lo,
            window_hi=window_hi,
            purpose=purpose,
            hop_limit=HOP_LIMIT,
            requester_bucket=requester_bucket,
            expires_window=now + EXPIRY_WINDOWS,
            nonce=secrets.token_bytes(12),
        )
        return replace(request, signature=self.__key.sign(request.signed_bytes()))


@dataclass
class RequestGuard:
    """Checks run by a responder before it looks at its evidence store."""

    member: int
    issuer_key: Ed25519PublicKey
    seen: set[bytes] = field(default_factory=set)
    answered: dict[tuple[int, bytes], int] = field(default_factory=lambda: defaultdict(int))
    refusals: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def refuse_reason(self, request: EvidenceRequest, now: int) -> str | None:
        reason = self._reason(request, now)
        if reason is None:
            self.seen.add(request.nonce)
            self.answered[(request.epoch, request.token)] += 1
        else:
            self.refusals[reason] += 1
        return reason

    def _reason(self, r: EvidenceRequest, now: int) -> str | None:
        try:
            self.issuer_key.verify(r.signature, r.signed_bytes())
        except InvalidSignature:
            return "bad_signature"
        if r.responder != self.member:
            return "wrong_responder"
        if now > r.expires_window:
            return "expired"
        if r.nonce in self.seen:
            return "replayed"
        if r.hop_limit < 1:
            return "hop_limit"
        if r.purpose not in PURPOSES:
            return "purpose"
        if self.answered[(r.epoch, r.token)] >= RATE_PER_TOKEN:
            return "rate_limited"
        return None


@dataclass
class ReceivedStore:
    """Evidence a requester received, kept for the retention period only."""

    items: list[tuple[int, EvidenceResponse]] = field(default_factory=list)

    def add(self, now: int, response: EvidenceResponse) -> None:
        self.items.append((now, response))

    def purge(self, now: int) -> int:
        before = len(self.items)
        self.items = [(t, r) for t, r in self.items if now - t <= RETENTION_WINDOWS]
        return before - len(self.items)
