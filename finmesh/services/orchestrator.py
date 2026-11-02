"""Orchestration for one bank on the demo path: alert -> session -> evidence -> card.

The online path is the demo slice's (``finmesh.demo.slice``), made durable:

1. **open** a session keyed by the alert (member, account, window). A replayed alert
   finds its session: a closed or failed one is returned as it is, so an alert never
   dispatches twice;
2. **plan**: tokenise the counterparties at other members through the token service,
   then sign one evidence request per counterparty and epoch. All planned requests are
   stored in one transaction before any is sent, so a resumed session reuses the same
   signed requests;
3. **request**: send each planned request that has no answer yet. A transport failure is
   retried with backoff, re-sending the *same* signed request, so the responder answers
   at most once (a request it already answered comes back ``refused: replayed``). A
   responder that stays unreachable is recorded as ``unavailable`` and the case goes on
   with partial evidence, flagged on the card;
4. **fuse** the bank's own probability with peers' alert flags and record probability
   buckets (noisy-OR with fixed weights, as in the slice), and write the incident card.
   The card never names an account at another member.

Failures before the plan is stored (the token service unreachable or over budget) are
retried on the next call; after ``max_attempts`` the session ends ``failed``. Every
session therefore ends ``closed`` or ``failed``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx2
import numpy as np

from finmesh.fusion.triage import BUCKET_MID
from finmesh.matching.tokens import BudgetExceeded, TokenClient, identifier
from finmesh.services.client import ServiceError
from finmesh.services.store import TERMINAL, SessionStore
from finmesh.services.wire import decode, encode
from finmesh.sharing.evidence import WIRE_FIELDS, bucket, load_evidence_schema
from finmesh.sharing.messages import EvidenceRequest, EvidenceResponse
from finmesh.sharing.node import BankNode, request_epochs
from finmesh.sharing.requests import RequestIssuer

FLAG_WEIGHT = 0.5  # noisy-OR weight of a peer's alert flag (the slice's fixed value)
LOOKBACK = 12  # 72 h of 6-hour windows
TRANSPORT_ERRORS = (httpx2.TransportError, ServiceError, OSError)
_PROB = WIRE_FIELDS.index("prob_bucket")


class Responder(Protocol):
    def respond(self, request: EvidenceRequest) -> EvidenceResponse: ...


@dataclass
class LocalNode:
    """An in-process node as a responder (the harness side of the contract)."""

    node: BankNode
    now: Callable[[], int]

    def respond(self, request: EvidenceRequest) -> EvidenceResponse:
        return self.node.respond(request, now=self.now())


@dataclass(frozen=True)
class Alert:
    member: int
    account: int  # the member's own account (never sent anywhere)
    window: int
    probability: float  # the member's calibrated probability for this account-window
    counterparties: tuple[tuple[int, int], ...]  # (member, account) from own payment data

    @property
    def key(self) -> str:
        return f"{self.member}:{self.account}:{self.window}"


@dataclass
class Orchestrator:
    member: int
    tokens: TokenClient
    issuer: RequestIssuer
    responders: dict[int, Responder]
    store: SessionStore
    first_window: int = 0
    lookback: int = LOOKBACK
    retries: int = 2
    backoff: float = 0.5
    max_attempts: int = 3
    sleep: Callable[[float], None] = time.sleep
    enrich: Callable[[Alert, dict[str, Any]], dict[str, Any]] | None = None
    prob_edges: tuple[float, ...] = field(default_factory=lambda: load_evidence_schema().prob_edges)

    # ------------------------------------------------------------------ public
    def handle(self, alert: Alert) -> dict[str, Any]:
        """Run (or resume) the session for ``alert``; returns the stored session."""
        if alert.member != self.member:
            raise ValueError("an orchestrator handles its own bank's alerts only")
        session, _ = self.store.open(alert.key, alert.member, alert.window)
        if session["state"] in TERMINAL:
            return session  # idempotent: a replayed alert never dispatches again
        attempts = self.store.bump_attempt(alert.key)
        if session["state"] == "opened":
            try:
                self.store.plan_requests(alert.key, self._plan(alert))
            except (BudgetExceeded, *TRANSPORT_ERRORS) as exc:
                if attempts >= self.max_attempts:
                    self.store.set_state(alert.key, "failed", f"{type(exc).__name__}: {exc}")
                else:
                    self.store.set_state(alert.key, "opened", f"retrying: {exc}")
                return self.store.session(alert.key)
        self._send(alert)
        card = self._card(alert)
        self.store.close_with_card(alert.key, card)
        return self.store.session(alert.key)

    # ------------------------------------------------------------------ steps
    def _plan(self, alert: Alert) -> list[tuple[int, int, dict[str, Any]]]:
        peers = sorted({cp for cp in alert.counterparties if cp[0] != self.member})
        mine = int(bucket(np.array([alert.probability]), self.prob_edges)[0])
        planned = []
        for epoch, lo, hi in request_epochs(alert.window, self.first_window, self.lookback):
            idents = [identifier(acct) for _, acct in peers]
            toks = self.tokens.tokens(epoch, idents) if idents else []
            for (cp_member, _), tok in zip(peers, toks, strict=True):
                if cp_member not in self.responders:
                    continue
                req = self.issuer.issue(
                    self.member, cp_member, tok, epoch, lo, hi, mine, now=alert.window
                )
                planned.append((cp_member, epoch, encode(req)))
        return planned

    def _send(self, alert: Alert) -> None:
        for r in self.store.requests(alert.key):
            if r["status"] not in ("planned", "sent"):
                continue  # answered or given up earlier: never sent again
            request = decode(r["request"], EvidenceRequest)
            responder = self.responders[r["responder"]]
            self.store.mark_sent(alert.key, r["idx"])
            for attempt in range(self.retries + 1):
                try:
                    response = responder.respond(request)
                except TRANSPORT_ERRORS:
                    if attempt == self.retries:
                        self.store.save_response(alert.key, r["idx"], "unavailable", None)
                        break
                    self.sleep(self.backoff * (2**attempt))
                    continue
                self.store.save_response(alert.key, r["idx"], response.status, encode(response))
                break

    def _card(self, alert: Alert) -> dict[str, Any]:
        rows = self.store.requests(alert.key)
        responses = [
            decode(r["response"], EvidenceResponse) for r in rows if r["response"] is not None
        ]
        flags = sum(int(x.alert) for x in responses)
        buckets = [x.record.values[_PROB] for x in responses if x.record is not None]
        keep = (1 - alert.probability) * (1 - FLAG_WEIGHT) ** flags
        for b in buckets:
            keep *= 1 - BUCKET_MID[min(int(b), len(BUCKET_MID) - 1)]
        fused = 1 - keep
        status = [r["status"] for r in rows]
        evidence = [
            {
                "member": r["responder"],
                "epoch": r["epoch"],
                "status": r["status"],
                "level": r["response"]["body"]["level"] if r["response"] else None,
                "peer_alert": bool(r["response"]["body"]["alert"]) if r["response"] else False,
                "has_record": bool(r["response"] and r["response"]["body"]["record"]),
            }
            for r in rows
        ]
        card: dict[str, Any] = {
            "session": alert.key,
            "member": alert.member,
            "window": alert.window,
            "own_probability": round(alert.probability, 4),
            "members_asked": len({r["responder"] for r in rows}),
            "requests": len(rows),
            "answered": status.count("ok") + status.count("no_record"),
            "refused": status.count("refused"),
            "unavailable": status.count("unavailable"),
            "evidence_incomplete": "unavailable" in status,
            "peer_alerts": flags,
            "peer_records": len(buckets),
            "fused_score": round(float(fused), 4),
            "suggested_action": "open case" if fused >= 0.5 or flags else "monitor",
            "evidence": evidence,
        }
        if self.enrich is not None:
            card.update(self.enrich(alert, card))
        return card


__all__ = ["Alert", "LocalNode", "Orchestrator", "Responder"]
