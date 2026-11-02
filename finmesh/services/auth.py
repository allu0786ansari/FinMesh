"""Service-to-service authentication for the token service (demo path).

A bank authenticates each call with an HMAC-SHA256 over its bank id, a timestamp, a
one-time nonce and the SHA-256 of the body, under a key shared with the token service
only. The service rejects an unknown bank, a bank that differs from the query's, a
timestamp outside the allowed skew, a nonce it has seen, and a bad MAC. Evidence requests
between nodes need no such header: they are signed by the request issuer (Ed25519) and
checked by the responder's guard.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass, field

SKEW_SECONDS = 120
NONCE_MEMORY = 100_000
HEADERS = ("x-finmesh-bank", "x-finmesh-time", "x-finmesh-nonce", "x-finmesh-auth")


def _mac(key: bytes, bank: int, stamp: int, nonce: str, body: bytes) -> str:
    digest = hashlib.sha256(body).hexdigest()
    return hmac.new(key, f"{bank}|{stamp}|{nonce}|{digest}".encode(), hashlib.sha256).hexdigest()


def sign_headers(key: bytes, bank: int, body: bytes, now: float | None = None) -> dict[str, str]:
    stamp = int(time.time() if now is None else now)
    nonce = secrets.token_hex(12)
    return {
        "X-FinMesh-Bank": str(bank),
        "X-FinMesh-Time": str(stamp),
        "X-FinMesh-Nonce": nonce,
        "X-FinMesh-Auth": _mac(key, bank, stamp, nonce, body),
    }


class AuthError(PermissionError):
    pass


@dataclass
class Verifier:
    keys: dict[int, bytes]
    skew: int = SKEW_SECONDS
    seen: OrderedDict[str, None] = field(default_factory=OrderedDict)

    def verify(self, headers: dict[str, str], body: bytes, now: float | None = None) -> int:
        """The authenticated bank id; raises :class:`AuthError` otherwise."""
        h = {k.lower(): v for k, v in headers.items()}
        if not all(k in h for k in HEADERS):
            raise AuthError("missing authentication headers")
        try:
            bank, stamp = int(h["x-finmesh-bank"]), int(h["x-finmesh-time"])
        except ValueError as exc:
            raise AuthError("malformed authentication headers") from exc
        key = self.keys.get(bank)
        if key is None:
            raise AuthError("unknown bank")
        current = time.time() if now is None else now
        if abs(current - stamp) > self.skew:
            raise AuthError("stale timestamp")
        nonce = h["x-finmesh-nonce"]
        if nonce in self.seen:
            raise AuthError("replayed nonce")
        if not hmac.compare_digest(_mac(key, bank, stamp, nonce, body), h["x-finmesh-auth"]):
            raise AuthError("bad signature")
        self.seen[nonce] = None
        while len(self.seen) > NONCE_MEMORY:
            self.seen.popitem(last=False)
        return bank


__all__ = ["AuthError", "Verifier", "sign_headers"]
