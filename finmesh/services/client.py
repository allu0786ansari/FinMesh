"""Clients of the demo path's services. They plug into the harness's interfaces:
:class:`HttpTokenTransport` is a token transport for :class:`TokenClient`, and
:class:`HttpNode` answers ``respond(request)`` like a :class:`BankNode`."""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx2

from finmesh.matching.tokens import BudgetExceeded
from finmesh.services.auth import sign_headers
from finmesh.services.wire import decode, encode
from finmesh.sharing.messages import (
    BlindedAnswer,
    BlindedQuery,
    EvidenceRequest,
    EvidenceResponse,
)


class ServiceError(RuntimeError):
    """A service refused or failed a call (not a protocol-level refusal)."""


def _raise(r: httpx2.Response) -> None:
    if r.status_code >= 400:
        detail = r.json().get("detail", r.text) if r.content else r.reason_phrase
        raise ServiceError(f"{r.request.url.path}: HTTP {r.status_code}: {detail}")


@dataclass
class HttpTokenTransport:
    """``(bank, epoch, blinded) -> evaluated`` over HTTP, authenticated as ``bank``."""

    http: httpx2.Client
    bank: int
    key: bytes

    def __call__(self, bank: int, epoch: int, blinded: list[bytes]) -> list[bytes]:
        body = json.dumps(encode(BlindedQuery(bank, epoch, tuple(blinded)))).encode()
        r = self.http.post(
            "/v1/evaluate",
            content=body,
            headers={"Content-Type": "application/json", **sign_headers(self.key, self.bank, body)},
        )
        if r.status_code == 429:
            raise BudgetExceeded(r.json().get("detail", "over budget"))
        _raise(r)
        return list(decode(r.json(), BlindedAnswer).points)


@dataclass
class HttpNode:
    """A remote bank node: ``respond(request)`` over HTTP."""

    http: httpx2.Client

    def respond(self, request: EvidenceRequest) -> EvidenceResponse:
        r = self.http.post("/v1/evidence", json=encode(request))
        _raise(r)
        return decode(r.json(), EvidenceResponse)

    def set_clock(self, admin_key: bytes, window: int) -> None:
        r = self.http.post(
            "/admin/clock", json={"window": window}, headers={"X-FinMesh-Admin": admin_key.hex()}
        )
        _raise(r)


__all__ = ["HttpNode", "HttpTokenTransport", "ServiceError"]
