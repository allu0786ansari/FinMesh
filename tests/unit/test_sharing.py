"""Week 6: tokens, evidence records, requests, responses and the protocol run."""

from __future__ import annotations

import pickle
from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from finmesh.matching import oprf
from finmesh.matching.tokens import (
    BudgetExceeded,
    HashTokenClient,
    TokenClient,
    TokenService,
    identifier,
)
from finmesh.sharing.evidence import WIRE_FIELDS, bucket, build_records, load_evidence_schema
from finmesh.sharing.messages import (
    Bus,
    EvidenceRecordWire,
    EvidenceResponse,
    MessageRejected,
    check,
)
from finmesh.sharing.node import BankNode, request_epochs
from finmesh.sharing.requests import (
    RATE_PER_TOKEN,
    RETENTION_WINDOWS,
    ReceivedStore,
    RequestGuard,
    RequestIssuer,
)
from finmesh.sharing.simulate import simulate


def _client(service: TokenService, bank: int) -> TokenClient:
    return TokenClient(bank, service.evaluate)


def test_tokens_agree_across_banks_and_change_across_epochs() -> None:
    service = TokenService(seed=b"\x01" * 32)
    a, b = _client(service, 0), _client(service, 1)
    ident = identifier(123456789)
    t0 = a.tokens(0, [ident])[0]
    assert b.tokens(0, [ident])[0] == t0  # same account, same epoch, any bank
    assert a.tokens(1, [ident])[0] != t0  # a new epoch key unlinks tokens
    assert t0 == service.audit_evaluate(0, ident)  # matches direct evaluation
    assert a.tokens(0, [identifier(1)])[0] != t0
    a.tokens(0, [ident])  # cached: no new query
    assert a.queries == 3 and service.used[(0, 0)] == 2


def test_token_service_meters_budgets_and_logs_counts_only() -> None:
    service = TokenService(seed=b"\x02" * 32, budget=3)
    client = _client(service, 7)
    client.tokens(0, [identifier(i) for i in range(3)])
    with pytest.raises(BudgetExceeded):
        client.tokens(0, [identifier(99)])
    assert [(e.bank, e.epoch, e.evaluated, e.refused) for e in service.log] == [
        (7, 0, 3, 0),
        (7, 0, 0, 1),
    ]
    assert client.tokens(1, [identifier(99)])  # a new epoch has a fresh budget


def test_no_key_ever_leaves_the_token_service() -> None:
    """CC5, runtime half: no public attribute, no repr, no pickle exposes a key."""
    service = TokenService()
    _client(service, 0).tokens(0, [identifier(5)])
    public = {k: v for k, v in vars(service).items() if not k.startswith("_")}
    assert not any(isinstance(v, oprf.KeyPair | bytes) for v in public.values())
    assert "secret" not in repr(service)
    with pytest.raises(TypeError):
        pickle.dumps(service)
    client = _client(service, 0)
    assert not any(isinstance(v, oprf.KeyPair) for v in vars(client).values())


def test_shared_key_control_lets_anyone_tokenise_offline() -> None:
    """The A1 control: every holder of the shared key computes the same tokens."""
    a, b = HashTokenClient(b"k" * 32, 0), HashTokenClient(b"k" * 32, 1)
    ident = identifier(42)
    assert a.tokens(0, [ident]) == b.tokens(0, [ident])
    assert a.tokens(0, [ident]) != a.tokens(1, [ident])


def test_bucket_and_records() -> None:
    assert bucket(np.array([0.0, 0.01, 0.3, np.nan]), (0.01, 0.05, 0.2, 0.5)).tolist() == [
        0,
        1,
        3,
        5,
    ]
    s = load_evidence_schema()
    frame = pl.DataFrame(
        {
            "member": [0, 0, 0],
            "account": [1, 2, 3],
            "window": [5, 5, 6],
            **{c[1]: [1.0, 2.0, None] for c in s.counters},
        },
        schema_overrides={"account": pl.UInt64},
    )
    prob = np.array([0.001, 0.3, 0.02])
    alerted = np.array([True, False, False])
    idx = np.array([[0, 1, 2]] * 3)
    recs = build_records(
        frame, prob, alerted, idx, np.ones((3, 3)), np.array([[0.5, 5.0, 20.0]] * 3)
    )
    assert recs["account"].to_list() == [1, 2, 3]  # account 1: alerted though below the floor
    assert recs["prob_bucket"].to_list() == [0, 3, 1]
    assert recs["dev0_magnitude"].to_list() == [0, 0, 0] and recs["dev2_magnitude"][0] == 3
    assert recs["c_delay_min_h"][2] == len(s.counters[-1][2]) + 1  # missing bucket
    assert set(WIRE_FIELDS) <= set(recs.columns) and "account" not in WIRE_FIELDS


def test_messages_are_allowlisted() -> None:
    check(EvidenceResponse(1, 0, "S1", "ok", True, 5))
    with pytest.raises(MessageRejected):
        check({"account": 1})  # not a message type
    with pytest.raises(MessageRejected):
        check(EvidenceResponse(1, 0, "S1", "ok", True, 5, EvidenceRecordWire(b"t", (1,))))
    with pytest.raises(MessageRejected):
        check(EvidenceResponse(1, 0, "S0", "ok"))  # S0 never responds
    with pytest.raises(MessageRejected):
        check(EvidenceRecordWire(b"t", (1.5,)))  # type: ignore[arg-type]


def _two_banks(level: str) -> tuple[RequestIssuer, BankNode, TokenService]:
    service = TokenService(seed=b"\x03" * 32)
    issuer = RequestIssuer()
    recs = pl.DataFrame(
        {
            "member": [1, 1],
            "account": [20, 20],
            "window": [5, 9],
            "alert": [True, False],
            **{f: [1, 2] for f in WIRE_FIELDS if f not in ("window", "alert")},
        },
        schema_overrides={"account": pl.UInt64},
    )
    node = BankNode(1, level, _client(service, 1), RequestGuard(1, issuer.public_key), recs)
    node.build_index()
    return issuer, node, service


@pytest.mark.parametrize("level", ["S1", "S2"])
def test_responses_follow_the_level(level: str) -> None:
    issuer, node, service = _two_banks(level)
    token = _client(service, 0).tokens(0, [identifier(20)])[0]
    r = node.respond(issuer.issue(0, 1, token, 0, 0, 9, 3, now=9), now=9)
    assert r.status == "ok" and r.alert and r.alert_window == 5
    if level == "S1":
        assert r.record is None
    else:
        assert r.record is not None and r.record.values[0] == 9  # latest window in range
    other = _client(service, 0).tokens(0, [identifier(21)])[0]
    assert node.respond(issuer.issue(0, 1, other, 0, 0, 9, 3, now=9), now=9).status == "no_record"
    early = node.respond(issuer.issue(0, 1, token, 0, 6, 9, 3, now=9), now=9)
    assert not early.alert  # the alert at window 5 is outside the requested range


def test_guard_refuses_forged_replayed_expired_and_probing_requests() -> None:
    issuer, node, service = _two_banks("S1")
    token = _client(service, 0).tokens(0, [identifier(20)])[0]
    req = issuer.issue(0, 1, token, 0, 0, 9, 3, now=9)
    assert node.respond(req, now=9).status == "ok"
    assert node.respond(req, now=9).status == "refused"  # replay
    forged = replace(issuer.issue(0, 1, token, 0, 0, 9, 3, now=9), window_lo=0, requester=5)
    assert node.respond(forged, now=9).status == "refused"  # signature no longer matches
    late = issuer.issue(0, 1, token, 0, 0, 9, 3, now=9)
    assert node.respond(late, now=20).status == "refused"  # expired
    wrong = issuer.issue(0, 2, token, 0, 0, 9, 3, now=9)
    assert node.respond(wrong, now=9).status == "refused"
    outsider = RequestIssuer().issue(0, 1, token, 0, 0, 9, 3, now=9)
    assert node.respond(outsider, now=9).status == "refused"  # unknown issuer
    for _ in range(RATE_PER_TOKEN + 3):
        node.respond(issuer.issue(0, 1, token, 0, 0, 9, 3, now=9), now=9)
    reasons = node.guard.refusals
    assert reasons["replayed"] == 1 and reasons["bad_signature"] == 2
    assert reasons["expired"] == 1 and reasons["wrong_responder"] == 1
    assert reasons["rate_limited"] == 4  # one answer already used, then the cap


def test_received_evidence_is_dropped_after_retention() -> None:
    store = ReceivedStore()
    store.add(0, EvidenceResponse(1, 0, "S1", "no_record"))
    store.add(10, EvidenceResponse(2, 0, "S1", "no_record"))
    assert store.purge(RETENTION_WINDOWS + 1) == 1 and len(store.items) == 1


def test_request_epochs_split_at_epoch_boundaries() -> None:
    assert request_epochs(30, 0, 12) == [(0, 19, 27), (1, 28, 30)]
    assert request_epochs(10, 5, 12) == [(0, 5, 10)]


def _protocol_case() -> tuple[pl.DataFrame, dict[int, pl.DataFrame], pl.DataFrame]:
    # a (bank 0) paid b (bank 1) in window 5; c (bank 0) paid d (bank 1), d not alerted.
    alerts = pl.DataFrame(
        {"member": [0, 1, 0], "account": [1, 2, 3], "window": [5, 6, 5], "prob_bucket": [4, 3, 4]},
        schema={
            "member": pl.Int32,
            "account": pl.UInt64,
            "window": pl.Int32,
            "prob_bucket": pl.Int8,
        },
    )
    edges = pl.DataFrame(
        {
            "src": [1, 3],
            "dst": [2, 4],
            "window": [5, 5],
            "src_member": [0, 0],
            "dst_member": [1, 1],
        },
        schema={
            "src": pl.UInt64,
            "dst": pl.UInt64,
            "window": pl.Int32,
            "src_member": pl.Int32,
            "dst_member": pl.Int32,
        },
    )

    def recs(
        member: int, accounts: list[int], windows: list[int], alert: list[bool]
    ) -> pl.DataFrame:
        n = len(accounts)
        return pl.DataFrame(
            {
                "member": [member] * n,
                "account": accounts,
                "window": windows,
                "alert": alert,
                **{f: [1] * n for f in WIRE_FIELDS if f not in ("window", "alert")},
            },
            schema_overrides={"account": pl.UInt64},
        )

    records = {0: recs(0, [1, 3], [5, 5], [True, True]), 1: recs(1, [2, 4], [6, 5], [True, False])}
    return alerts, records, edges


def test_protocol_links_alerts_across_banks_at_s1_and_s2_only() -> None:
    alerts, records, edges = _protocol_case()
    s0 = simulate("S0", alerts, records, edges, 0, 12)
    assert s0.links.height == 0 and s0.stats["requests"] == 0
    for level in ("S1", "S2"):
        run = simulate(level, alerts, records, edges, 0, 12)
        # Bank 0's alert on a (window 5) asks bank 1 about b; b's alert is at window 6,
        # after the request time, so it is not seen then. Bank 1's alert on b (window 6)
        # asks bank 0 about a, alerted at window 5: that response links them.
        pairs = set(run.links.select("account_a", "account_b").iter_rows())
        assert pairs == {(2, 1)}
        assert run.stats["requests"] == 3  # a->b, c->d, b->a
        assert set(run.stats["messages"]) <= {
            "BlindedQuery",
            "BlindedAnswer",
            "EvidenceRequest",
            "EvidenceResponse",
        }
        assert run.stats["refusals"] == {}


def test_bus_counts_every_message() -> None:
    bus = Bus()
    bus.send(EvidenceResponse(1, 0, "S2", "no_record"))
    assert bus.counts["EvidenceResponse"] == 1
    with pytest.raises(MessageRejected):
        bus.send(object())
