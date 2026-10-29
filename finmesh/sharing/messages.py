"""Messages that may leave a node, and the bus that enforces it (criterion CC5).

Only the dataclasses in :data:`ALLOWLIST` cross a node boundary. Each field
holds a primitive (int, bool, bytes, str enum or a tuple of ints); nothing
named like an account, amount or raw score exists in any of them, which a
contract test checks. The in-process :class:`Bus` validates every message
before delivery and keeps counts by type for the run report.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields
from typing import Any

LEVELS: tuple[str, ...] = ("S0", "S1", "S2", "S3", "S4", "PD")
PURPOSES: tuple[str, ...] = ("alert_triage",)
STATUSES: tuple[str, ...] = ("ok", "no_record", "refused")


@dataclass(frozen=True)
class BlindedQuery:
    """Bank -> token service: blinded points for one epoch."""

    bank: int
    epoch: int
    points: tuple[bytes, ...]


@dataclass(frozen=True)
class BlindedAnswer:
    """Token service -> bank: evaluated points, same order."""

    points: tuple[bytes, ...]


@dataclass(frozen=True)
class EvidenceRequest:
    """Requester -> responder, signed by the request issuer, usable once."""

    request_id: int
    requester: int
    responder: int
    token: bytes
    epoch: int
    window_lo: int
    window_hi: int
    purpose: str
    hop_limit: int
    requester_bucket: int
    expires_window: int
    nonce: bytes
    signature: bytes = b""

    def signed_bytes(self) -> bytes:
        """Canonical bytes covered by the signature (everything but the signature)."""
        parts = [
            self.request_id,
            self.requester,
            self.responder,
            self.token.hex(),
            self.epoch,
            self.window_lo,
            self.window_hi,
            self.purpose,
            self.hop_limit,
            self.requester_bucket,
            self.expires_window,
            self.nonce.hex(),
        ]
        return "|".join(str(p) for p in parts).encode()


@dataclass(frozen=True)
class EvidenceRecordWire:
    """The minimised record (S2): buckets only, named by the requester's token."""

    token: bytes
    values: tuple[int, ...]  # WIRE_FIELDS (S2, S3 noised, PD) or S4_FIELDS (S4), in order


@dataclass(frozen=True)
class EvidenceResponse:
    """Responder -> requester, at the responder's sharing level."""

    request_id: int
    responder: int
    level: str
    status: str
    alert: bool = False
    alert_window: int = -1
    record: EvidenceRecordWire | None = None


ALLOWLIST: tuple[type, ...] = (
    BlindedQuery,
    BlindedAnswer,
    EvidenceRequest,
    EvidenceResponse,
    EvidenceRecordWire,
)
_PRIMITIVES = (int, bool, bytes, str)


class MessageRejected(PermissionError):
    """A message failed the allowlist or its level's policy."""


def check(message: Any) -> None:
    """Raise :class:`MessageRejected` unless ``message`` may leave a node."""
    if type(message) not in ALLOWLIST:
        raise MessageRejected(f"{type(message).__name__} is not an allowlisted message")
    for f in fields(message):
        value = getattr(message, f.name)
        if isinstance(value, tuple):
            if not all(isinstance(v, _PRIMITIVES) for v in value):
                raise MessageRejected(f"{f.name} holds a non-primitive")
        elif value is not None and not isinstance(value, (*_PRIMITIVES, EvidenceRecordWire)):
            raise MessageRejected(f"{f.name} has type {type(value).__name__}")
        if isinstance(value, EvidenceRecordWire):
            check(value)
    if isinstance(message, EvidenceResponse):
        if message.level not in LEVELS or message.status not in STATUSES:
            raise MessageRejected("unknown level or status")
        if message.level == "S0":
            raise MessageRejected("S0 never responds")
        if message.level == "S1" and message.record is not None:
            raise MessageRejected("S1 responses carry no record")
    if isinstance(message, EvidenceRequest) and message.purpose not in PURPOSES:
        raise MessageRejected("undeclared purpose")


class Bus:
    """In-process transport: validates and counts every message it carries."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()

    def send(self, message: Any) -> Any:
        check(message)
        self.counts[type(message).__name__] += 1
        return message
