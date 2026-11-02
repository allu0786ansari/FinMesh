"""Week 15 part 2: orchestration with durable sessions, idempotency, fault handling,
four-eyes approval and persistent token budgets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import polars as pl
import pytest
from fastapi.testclient import TestClient

from finmesh.matching.tokens import BudgetExceeded, TokenClient, TokenService, identifier
from finmesh.services.apps import node_app, token_app
from finmesh.services.client import HttpNode, HttpTokenTransport
from finmesh.services.orchestrator import Alert, LocalNode, Orchestrator
from finmesh.services.store import BudgetLedger, SessionStore
from finmesh.sharing.evidence import WIRE_FIELDS
from finmesh.sharing.messages import EvidenceRequest, EvidenceResponse
from finmesh.sharing.node import BankNode
from finmesh.sharing.requests import RequestGuard, RequestIssuer

KEYS = {0: b"k0" * 16, 1: b"k1" * 16, 2: b"k2" * 16}
ADMIN = b"admin-key-0123456789abcdef"
ALERT = Alert(member=0, account=7, window=9, probability=0.2,
              counterparties=((1, 20), (1, 21), (2, 30), (0, 8)))  # fmt: skip


def _node(
    member: int, service: TokenService, issuer: RequestIssuer, accounts: list[int]
) -> BankNode:
    n = len(accounts)
    recs = pl.DataFrame(
        {
            "member": [member] * n,
            "account": accounts,
            "window": [5] * n,
            "alert": [True] + [False] * (n - 1),
            **{f: [3] * n for f in WIRE_FIELDS if f not in ("window", "alert")},
        },
        schema_overrides={"account": pl.UInt64},
    )
    node = BankNode(member, "S2", TokenClient(member, service.evaluate),
                    RequestGuard(member, issuer.public_key), recs)  # fmt: skip
    node.build_index()
    return node


class Counting:
    """Wraps a responder: counts calls, and can fail the first ``fail`` calls."""

    def __init__(self, inner: Any, fail: int = 0, exc: BaseException | None = None) -> None:
        self.inner, self.fail, self.calls = inner, fail, 0
        self.exc = exc or httpx.ConnectError("node down")

    def respond(self, request: EvidenceRequest) -> EvidenceResponse:
        self.calls += 1
        if self.calls <= self.fail:
            raise self.exc
        return self.inner.respond(request)


def _world(tmp_path: Path, **kw: Any) -> tuple[Orchestrator, dict[int, Counting], TokenService]:
    service = TokenService(seed=b"\x11" * 32)
    issuer = RequestIssuer()
    nodes = {1: _node(1, service, issuer, [20, 21]), 2: _node(2, service, issuer, [30])}
    responders = {
        m: Counting(LocalNode(n, lambda: 9), **kw.pop(f"r{m}", {})) for m, n in nodes.items()
    }
    orch = Orchestrator(0, TokenClient(0, service.evaluate), issuer, dict(responders),
                        SessionStore(tmp_path / "s.db"), sleep=lambda _: None, **kw)  # fmt: skip
    return orch, responders, service


def test_alert_becomes_a_card_without_naming_other_members_accounts(tmp_path: Path) -> None:
    orch, _, _ = _world(tmp_path)
    s = orch.handle(ALERT)
    card = s["card"]
    assert s["state"] == "closed" and card["requests"] == 3 and card["members_asked"] == 2
    assert card["answered"] == 3 and card["peer_alerts"] == 2 and card["peer_records"] == 3
    assert card["fused_score"] > ALERT.probability and card["suggested_action"] == "open case"
    assert not card["evidence_incomplete"]
    assert "account" not in card and "token" not in str(card)  # nothing names a peer account
    assert set(card) >= {"session", "member", "window", "evidence"}
    assert all(set(e) == {"member", "epoch", "status", "level", "peer_alert", "has_record"}
               for e in card["evidence"])  # fmt: skip


def test_a_replayed_alert_never_dispatches_twice(tmp_path: Path) -> None:
    orch, responders, _ = _world(tmp_path)
    first = orch.handle(ALERT)
    calls = {m: r.calls for m, r in responders.items()}
    again = orch.handle(ALERT)
    assert again["card"] == first["card"] and again["attempts"] == first["attempts"]
    assert {m: r.calls for m, r in responders.items()} == calls


def test_a_crash_mid_session_resumes_without_resending_answered_requests(tmp_path: Path) -> None:
    class Crash(BaseException):  # an abrupt stop, not a handled transport error
        pass

    orch, responders, service = _world(tmp_path, r2={"fail": 1, "exc": Crash()})
    with pytest.raises(Crash):
        orch.handle(ALERT)
    s = orch.store.session(ALERT.key)
    assert s["state"] == "planned"
    statuses = [r["status"] for r in orch.store.requests(ALERT.key)]
    assert statuses.count("ok") == 2 and statuses.count("sent") == 1
    # A new orchestrator process on the same database resumes the session.
    restarted = Orchestrator(0, TokenClient(0, service.evaluate), orch.issuer,
                             dict(responders), SessionStore(tmp_path / "s.db"),
                             sleep=lambda _: None)  # fmt: skip
    done = restarted.handle(ALERT)
    assert done["state"] == "closed" and done["card"]["answered"] == 3
    assert responders[1].calls == 2  # member 1's two requests were never sent again
    assert responders[2].calls == 2  # the crashed send, re-sent once with the same signature


def test_an_unreachable_member_gives_a_flagged_partial_case(tmp_path: Path) -> None:
    orch, responders, _ = _world(tmp_path, r2={"fail": 99}, retries=2)
    s = orch.handle(ALERT)
    card = s["card"]
    assert s["state"] == "closed" and card["unavailable"] == 1 and card["evidence_incomplete"]
    assert responders[2].calls == 3  # first try plus two retries
    assert card["answered"] == 2


def test_a_transient_failure_is_retried_with_the_same_signed_request(tmp_path: Path) -> None:
    orch, responders, _ = _world(tmp_path, r2={"fail": 1})
    s = orch.handle(ALERT)
    assert s["card"]["answered"] == 3 and responders[2].calls == 2
    assert not s["card"]["evidence_incomplete"]


def test_token_service_failure_ends_failed_after_max_attempts(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "s.db")

    def down(bank: int, epoch: int, blinded: list[bytes]) -> list[bytes]:
        raise httpx.ConnectError("token service down")

    orch = Orchestrator(0, TokenClient(0, down), RequestIssuer(), {}, store,
                        sleep=lambda _: None, max_attempts=2)  # fmt: skip
    one = orch.handle(ALERT)
    assert one["state"] == "opened" and "retrying" in one["error"]
    two = orch.handle(ALERT)
    assert two["state"] == "failed" and "ConnectError" in two["error"]
    assert orch.handle(ALERT)["state"] == "failed"  # terminal: nothing more is tried

    def over(bank: int, epoch: int, blinded: list[bytes]) -> list[bytes]:
        raise BudgetExceeded("over budget")

    other = Alert(0, 8, 9, 0.1, ((1, 20),))
    orch2 = Orchestrator(0, TokenClient(0, over), RequestIssuer(), {1: Counting(None)}, store,
                         sleep=lambda _: None, max_attempts=1)  # fmt: skip
    assert orch2.handle(other)["state"] == "failed"


def test_high_impact_actions_need_a_second_person(tmp_path: Path) -> None:
    orch, _, _ = _world(tmp_path)
    orch.handle(ALERT)
    store = orch.store
    note = store.record_action(ALERT.key, "add_note", "analyst_a", "looked at it")
    assert note["status"] == "done"
    esc = store.record_action(ALERT.key, "escalate", "analyst_a")
    assert esc["status"] == "pending_approval"
    with pytest.raises(PermissionError):
        store.decide(esc["id"], "analyst_a", approve=True)  # no self-approval
    assert store.decide(esc["id"], "lead_b", approve=True)["status"] == "approved"
    with pytest.raises(ValueError):
        store.decide(esc["id"], "lead_c", approve=False)  # already decided
    with pytest.raises(KeyError):
        store.record_action("no:such:session", "add_note", "analyst_a")


def test_orchestrator_over_http_matches_in_process(tmp_path: Path) -> None:
    """Contract: the same alert through HTTP services gives the same card."""
    issuer = RequestIssuer()
    s_local, s_http = TokenService(seed=b"\x12" * 32), TokenService(seed=b"\x12" * 32)
    in_proc = Orchestrator(
        0, TokenClient(0, s_local.evaluate), issuer,
        {1: LocalNode(_node(1, s_local, issuer, [20, 21]), lambda: 9),
         2: LocalNode(_node(2, s_local, issuer, [30]), lambda: 9)},
        SessionStore(tmp_path / "a" / "s.db"), sleep=lambda _: None,
    )  # fmt: skip
    token_http = TestClient(token_app(s_http, KEYS))
    over_http = Orchestrator(
        0, TokenClient(0, HttpTokenTransport(token_http, 0, KEYS[0])), issuer,
        {1: HttpNode(TestClient(node_app(_node(1, s_http, issuer, [20, 21]), ADMIN, 9))),
         2: HttpNode(TestClient(node_app(_node(2, s_http, issuer, [30]), ADMIN, 9)))},
        SessionStore(tmp_path / "b" / "s.db"), sleep=lambda _: None,
    )  # fmt: skip
    a, b = in_proc.handle(ALERT)["card"], over_http.handle(ALERT)["card"]
    assert a == b


def test_token_budget_survives_a_restart(tmp_path: Path) -> None:
    ledger_path = tmp_path / "budget.db"

    def client(service: TokenService) -> TokenClient:
        app = token_app(service, KEYS, BudgetLedger(ledger_path))
        return TokenClient(0, HttpTokenTransport(TestClient(app), 0, KEYS[0]))

    client(TokenService(seed=b"\x13" * 32, budget=3)).tokens(0, [identifier(a) for a in (1, 2)])
    restarted = client(TokenService(seed=b"\x13" * 32, budget=3))  # a fresh process
    restarted.tokens(0, [identifier(3)])  # the third evaluation still fits
    with pytest.raises(BudgetExceeded):
        restarted.tokens(0, [identifier(4)])  # the restart did not reset the budget
    calls = BudgetLedger(ledger_path).calls()
    assert [(c["evaluated"], c["refused"]) for c in calls] == [(2, 0), (1, 0), (0, 1)]
    assert BudgetLedger(ledger_path).used(0, 0) == 3
