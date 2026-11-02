"""Week 16: the demo world, the analyst console and the privacy ledger."""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from fastapi.testclient import TestClient

from finmesh.attribution.claims import claim_check
from finmesh.matching.tokens import TokenClient, TokenService
from finmesh.services.console import console_app
from finmesh.services.enrich import case_summary
from finmesh.services.ledger import privacy_ledger
from finmesh.services.orchestrator import Alert, LocalNode, Orchestrator
from finmesh.services.store import SessionStore
from finmesh.sharing.evidence import WIRE_FIELDS
from finmesh.sharing.node import BankNode
from finmesh.sharing.requests import RequestGuard, RequestIssuer

FEATS = {"fan_in": 1.0, "fan_out": 12.0, "pass_through": 0.0, "cyc2": 0.0, "cyc3": 0.0,
         "cyc4": 0.0, "sg_out_max": 0.0, "sg_in_max": 0.0}  # fmt: skip


def test_issuer_key_survives_a_restart() -> None:
    from finmesh.services.world import issuer_from, new_issuer_key

    raw = new_issuer_key()
    a, b = issuer_from(raw), issuer_from(raw)  # before and after a restart
    req = b.issue(0, 1, b"t" * 16, 0, 0, 9, 3, now=9)
    guard = RequestGuard(1, a.public_key)  # nodes keep trusting the original public key
    assert guard.refuse_reason(req, now=9) is None
    outsider = RequestIssuer().issue(0, 1, b"t" * 16, 0, 0, 9, 3, now=9)
    assert guard.refuse_reason(outsider, now=9) == "bad_signature"


def test_case_summary_is_claim_consistent_and_its_hint_comes_from_the_catalogue() -> None:
    evidence = [{"member": 1, "status": "ok"}, {"member": 2, "status": "unavailable"}]
    card = {"peer_alerts": 1, "peer_records": 2, "members_asked": 2, "evidence_incomplete": True,
            "evidence": evidence}  # fmt: skip
    s = case_summary(FEATS, card)
    assert s["typology_hint"] == "FAN-OUT" and s["review_actions"]
    assert "12 (many payees)" in s["summary"] and "0.00 (none passed on)" in s["summary"]
    assert "could not be reached" in s["summary"] and "0 (none) short money loops" in s["summary"]
    ev = {"own_max_fan_out": "12", "own_max_fan_in": "1", "own_mean_pass_through": "0.00",
          "own_max_cycles": "0"}  # fmt: skip
    assert claim_check(s["summary"], ev)["consistent"]
    assert "hint" in s["typology_hint_basis"]
    empty = case_summary({}, {"evidence": []})
    assert "not available" in empty["summary"] and empty["typology_hint"]


def _node(
    member: int, service: TokenService, issuer: RequestIssuer, accounts: list[int]
) -> BankNode:
    n = len(accounts)
    recs = pl.DataFrame(
        {"member": [member] * n, "account": accounts, "window": [5] * n,
         "alert": [True] + [False] * (n - 1),
         **{f: [3] * n for f in WIRE_FIELDS if f not in ("window", "alert")}},
        schema_overrides={"account": pl.UInt64},
    )  # fmt: skip
    node = BankNode(member, "S2", TokenClient(member, service.evaluate),
                    RequestGuard(member, issuer.public_key), recs)  # fmt: skip
    node.build_index()
    return node


@pytest.fixture()
def worked(tmp_path: Path) -> tuple[SessionStore, dict[str, Any]]:
    service = TokenService(seed=b"\x21" * 32)
    issuer = RequestIssuer()
    nodes = {1: _node(1, service, issuer, [20, 21]), 2: _node(2, service, issuer, [30])}
    store = SessionStore(tmp_path / "s.db")

    def enrich(alert: Alert, card: dict[str, Any]) -> dict[str, Any]:
        return case_summary(FEATS, card)

    orch = Orchestrator(0, TokenClient(0, service.evaluate), issuer,
                        {m: LocalNode(n, lambda: 9) for m, n in nodes.items()}, store,
                        sleep=lambda _: None, enrich=enrich)  # fmt: skip
    for acct, prob, cps in (
        (7, 0.2, ((1, 20), (2, 30))),
        (8, 0.6, ((1, 21),)),
        (9, 0.05, ((1, 99),)),
    ):
        orch.handle(Alert(0, acct, 9, prob, cps))
    meta = {"dataset": "TEST", "level": "S2", "members": [0, 1, 2],
            "accounts_per_member": {0: 1000, 1: 1000, 2: 1000}, "token_budget": 100}  # fmt: skip
    return store, meta


def test_privacy_ledger_counts_every_disclosure(
    worked: tuple[SessionStore, dict[str, Any]],
) -> None:
    store, meta = worked
    L = privacy_ledger(store, None, meta)
    by = {m["member"]: m for m in L["evidence"]["by_member"]}
    assert by[0]["requests_sent"] == 4 and by[1]["requests"] == 3 and by[2]["requests"] == 1
    assert by[1]["records_released"] == 2 and by[1]["no_record"] == 1  # account 99 is unknown
    assert by[1]["alert_flags"] == 1 and by[2]["records_released"] == 1
    assert len(L["requests"]) == 4 and not L["model"]["shared_model"]
    assert not L["evidence"]["differentially_private"]
    assert all("account" not in r and "token" not in r for r in L["requests"])


def test_console_queue_case_actions_and_ledger(worked: tuple[SessionStore, dict[str, Any]]) -> None:
    store, meta = worked
    c = TestClient(console_app(store, None, meta))
    assert "FinMesh analyst console" in c.get("/").text
    assert c.get("/api/meta").json()["high_impact"] == ["escalate", "file_report", "freeze_account"]
    q = c.get("/api/queue").json()
    scores = [r["fused_score"] for r in q]
    assert len(q) == 3 and scores == sorted(scores, reverse=True) and q[0]["rank"] == 1
    assert "toFixed(3)" in c.get("/").text  # scores always show three decimals
    assert c.get("/api/queue?member=5").json() == []
    key = q[0]["key"]
    case = c.get(f"/api/session/{key}").json()
    assert case["card"]["typology_hint"] and case["card"]["summary"] and case["actions"] == []
    assert c.get("/api/session/0:1:2").status_code == 404
    bad = c.post(f"/api/session/{key}/actions", json={"action": "delete_all", "actor": "a"})
    assert bad.status_code == 400
    assert (
        c.post(f"/api/session/{key}/actions", json={"action": "monitor", "actor": ""}).status_code
        == 422
    )
    note = c.post(f"/api/session/{key}/actions", json={"action": "add_note", "actor": "ana"}).json()
    assert note["status"] == "done"
    esc = c.post(f"/api/session/{key}/actions", json={"action": "escalate", "actor": "ana"}).json()
    assert esc["status"] == "pending_approval"
    assert c.get("/api/queue").json()[0]["pending_approvals"] == 1
    url = f"/api/actions/{esc['id']}/decide"
    assert c.post(url, json={"approver": "ana", "approve": True}).status_code == 403  # four eyes
    assert c.post(url, json={"approver": "lead", "approve": True}).json()["status"] == "approved"
    assert c.post(url, json={"approver": "lead2", "approve": False}).status_code == 409
    assert (
        c.post("/api/actions/999/decide", json={"approver": "x", "approve": True}).status_code
        == 404
    )
    assert len(c.get("/api/ledger").json()["requests"]) == 4


def test_demo_world_on_the_fixture_end_to_end(
    fixture_paths: Any, ingested: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import finmesh.training.x1 as x1
    from finmesh.eval.budgets import Budget
    from finmesh.eval.g0 import run_g0
    from finmesh.eval.universe import build_universe
    from finmesh.features.build import build_features
    from finmesh.services.store import BudgetLedger
    from finmesh.services.world import build_world, load_world, run_world

    run_g0(fixture_paths)
    build_universe(fixture_paths, "B8")
    build_features(fixture_paths, "B8")
    monkeypatch.setattr(x1, "PRIMARY", Budget("per_1000_per_day", 300.0))  # as the slice test
    folder = tmp_path / "demo"
    meta = build_world(fixture_paths, folder, n_alerts=6)
    assert meta["alerts"] == 6 and meta["level"] == "S2"
    assert stat.S_IMODE((folder / "secrets.json").stat().st_mode) == 0o600
    world = load_world(folder)
    assert len(world.alerts) == 6 and world.records
    assert all(a["counterparties"] for a in world.alerts)
    r = run_world(world)
    assert r["sessions"] == 6 and r["states"]["closed"] == 6
    again = run_world(load_world(folder))  # a replayed run dispatches nothing new
    assert again["states"]["closed"] == 6
    store = SessionStore(folder / "sessions.db")
    L = privacy_ledger(store, BudgetLedger(folder / "budget.db"), world.meta)
    n_requests = len(L["requests"])
    assert n_requests > 0 and L["tokens"] and all(t["refused"] == 0 for t in L["tokens"])
    c = TestClient(console_app(store, BudgetLedger(folder / "budget.db"), world.meta))
    q = c.get("/api/queue").json()
    assert len(q) == 6 and all(x["state"] == "closed" for x in q)
    card = c.get(f"/api/session/{q[0]['key']}").json()["card"]
    assert card["summary"] and card["typology_hint"] and card["requests"] >= 1
    assert len(privacy_ledger(store, None, world.meta)["requests"]) == n_requests


def test_queue_breaks_ties_by_peer_evidence_and_ranks_across_members(tmp_path: Path) -> None:
    from finmesh.services.console import queue

    store = SessionStore(tmp_path / "q.db")
    cards = {  # (member, account, window): (fused, peer alerts, peer records)
        (0, 1, 5): (1.0, 0, 0), (0, 2, 5): (1.0, 2, 1), (0, 3, 4): (1.0, 2, 2),
        (1, 4, 6): (0.9, 0, 0), (1, 5, 6): (1.0, 1, 0),
    }  # fmt: skip
    for (m, a, w), (f, pa, pr) in cards.items():
        store.open(f"{m}:{a}:{w}", m, w)
        store.close_with_card(
            f"{m}:{a}:{w}", {"fused_score": f, "peer_alerts": pa, "peer_records": pr}
        )
    rows = queue(store, {"accounts_per_member": {0: 1000, 1: 1000}}, None)
    assert [r["key"] for r in rows] == ["0:3:4", "0:2:5", "1:5:6", "0:1:5", "1:4:6"]
    assert {r["key"]: r["rank"] for r in rows} == {
        "0:3:4": 1, "0:2:5": 2, "0:1:5": 3, "1:5:6": 1, "1:4:6": 2
    }  # fmt: skip
    assert [r["key"] for r in queue(store, {}, 1)] == ["1:5:6", "1:4:6"]
